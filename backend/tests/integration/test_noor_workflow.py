"""T170-T176: Integration tests for the Noor allocation workflow (Group E).

These exercise the route → workflow → repository wiring with the database layer
mocked. The repo's pure logic (cooldown timestamps, reference IDs) is asserted
through the workflow's observable side-effects.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# ─── Helpers ──────────────────────────────────────────────────────

def _build_user(**overrides):
    base = dict(
        id=uuid.uuid4(),
        wp_user_id=42,
        email="client@example.com",
        display_name="Test Client",
        role="client",
        status="active",
    )
    base.update(overrides)
    user = MagicMock()
    for k, v in base.items():
        setattr(user, k, v)
    return user


def _build_noor_row(*, status="pending", cooldown_until=None, **overrides):
    """Mimic NoorAllocationRequest with the attributes the routes touch."""
    now = datetime.now(timezone.utc)
    base = dict(
        id=uuid.uuid4(),
        reference_id="NOR-ABCDEF12",
        user_id=uuid.uuid4(),
        full_name="Test Client",
        purpose="A celebration piece",
        timeline="3 months",
        delivery_location="London, UK",
        contact_method="email",
        contact_details="client@example.com",
        status=status,
        cooldown_until=cooldown_until,
        submitted_at=now,
        reviewed_at=None,
        reviewed_by=None,
        internal_notes=None,
    )
    base.update(overrides)
    row = MagicMock()
    for k, v in base.items():
        setattr(row, k, v)
    return row


def _valid_payload():
    return {
        "full_name": "Test Client",
        "purpose": "A keepsake for a milestone birthday.",
        "timeline": "Within 3 months",
        "delivery_location": "London, UK",
        "contact_method": "email",
        "contact_details": "client@example.com",
    }


# ─── User-facing routes (T170-T172, T175) ─────────────────────────

@pytest.mark.asyncio
async def test_create_request_ok():
    """T170: Valid submission with no blocking row → 201 and reference ID."""
    from app.auth.dependencies import get_current_user
    from app.db.session import get_session
    from app.main import app

    user = _build_user()
    inserted = _build_noor_row(user_id=user.id)

    async def _session_override():
        yield MagicMock()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_session] = _session_override

    try:
        with patch(
            "app.services.noor_workflow.noor_repo.user_has_active",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.noor_workflow.noor_repo.create",
            new_callable=AsyncMock,
            return_value=inserted,
        ), patch(
            "app.services.noor_workflow._fire_notifications_on_create",
            new_callable=AsyncMock,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/v1/noor-requests", json=_valid_payload())
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "success"
    assert body["reference_id"] == "NOR-ABCDEF12"
    assert "concierge" in body["message"].lower()


@pytest.mark.asyncio
async def test_blocks_pending():
    """T171: Submission while a pending request exists → 409 NoorPendingConflict."""
    from app.auth.dependencies import get_current_user
    from app.db.session import get_session
    from app.main import app

    user = _build_user()
    blocking = _build_noor_row(status="pending", user_id=user.id)

    async def _session_override():
        yield MagicMock()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_session] = _session_override

    try:
        with patch(
            "app.services.noor_workflow.noor_repo.user_has_active",
            new_callable=AsyncMock,
            return_value=blocking,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/v1/noor-requests", json=_valid_payload())
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 409
    assert "pending" in resp.json()["error"].lower()


@pytest.mark.asyncio
async def test_blocks_cooldown():
    """T172: Approved request still inside cooldown_until → 409 CooldownActive."""
    from app.auth.dependencies import get_current_user
    from app.db.session import get_session
    from app.main import app

    user = _build_user()
    future = datetime.now(timezone.utc) + timedelta(days=30)
    blocking = _build_noor_row(status="approved", cooldown_until=future, user_id=user.id)

    async def _session_override():
        yield MagicMock()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_session] = _session_override

    try:
        with patch(
            "app.services.noor_workflow.noor_repo.user_has_active",
            new_callable=AsyncMock,
            return_value=blocking,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/v1/noor-requests", json=_valid_payload())
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 409
    assert "cooldown" in resp.json()["error"].lower()


@pytest.mark.asyncio
async def test_anonymous_forbidden():
    """T175: POST without Bearer token → 401."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/v1/noor-requests", json=_valid_payload())

    assert resp.status_code == 401


# ─── Repo-level cooldown semantics (T173, T174) ───────────────────

@pytest.mark.asyncio
async def test_approve_sets_cooldown():
    """T173: review(status='approved') writes cooldown_until = now + cooldown_days."""
    from app.db.repositories import noor_requests as noor_repo

    captured: dict = {}

    class _FakeStmt:
        def values(self, **kwargs):
            captured.update(kwargs)
            return self

    def _fake_update(_model):
        return _FakeStmt()

    def _fake_where(self, *args, **kwargs):  # noqa: ARG001
        return self

    _FakeStmt.where = _fake_where  # type: ignore[attr-defined]

    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()

    request_id = uuid.uuid4()
    refreshed = _build_noor_row(status="approved")

    with patch.object(noor_repo, "update", _fake_update), patch.object(
        noor_repo, "get_by_id", new_callable=AsyncMock, return_value=refreshed
    ):
        result = await noor_repo.review(
            session,
            request_id,
            status="approved",
            cooldown_days=90,
            reviewed_by="concierge@aueshah.com",
        )

    assert result is refreshed
    assert captured["status"] == "approved"
    assert "cooldown_until" in captured
    delta = captured["cooldown_until"] - datetime.now(timezone.utc)
    assert timedelta(days=89, hours=23) < delta <= timedelta(days=90)


@pytest.mark.asyncio
async def test_decline_sets_cooldown():
    """T174: review(status='declined') sets cooldown_until → user cannot resubmit during window."""
    from app.db.repositories import noor_requests as noor_repo

    captured: dict = {}

    class _FakeStmt:
        def values(self, **kwargs):
            captured.update(kwargs)
            return self

        def where(self, *args, **kwargs):  # noqa: ARG002
            return self

    def _fake_update(_model):
        return _FakeStmt()

    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()

    refreshed = _build_noor_row(status="declined")

    with patch.object(noor_repo, "update", _fake_update), patch.object(
        noor_repo, "get_by_id", new_callable=AsyncMock, return_value=refreshed
    ):
        await noor_repo.review(
            session,
            uuid.uuid4(),
            status="declined",
            cooldown_days=365,
        )

    assert captured["status"] == "declined"
    assert "cooldown_until" in captured
    delta = captured["cooldown_until"] - datetime.now(timezone.utc)
    assert timedelta(days=364, hours=23) < delta <= timedelta(days=365)


# ─── Admin routes (T176) ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_token_required():
    """T176: PATCH without X-Admin-Token → 401."""
    from app.db.session import get_session
    from app.main import app

    async def _session_override():
        yield MagicMock()

    app.dependency_overrides[get_session] = _session_override
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.patch(
                f"/v1/admin/noor-requests/{uuid.uuid4()}",
                json={"status": "approved"},
            )
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_review_with_token_succeeds():
    """T176 (positive): valid X-Admin-Token + approve → 200 with updated row."""
    from app.db.session import get_session
    from app.main import app
    from app.config.settings import settings

    async def _session_override():
        yield MagicMock()

    app.dependency_overrides[get_session] = _session_override

    request_id = uuid.uuid4()
    future = datetime.now(timezone.utc) + timedelta(days=90)
    reviewed = _build_noor_row(
        status="approved",
        cooldown_until=future,
        reference_id="NOR-DEADBEEF",
    )
    reviewed.reviewed_at = datetime.now(timezone.utc)

    original_token = settings.admin_api_token
    settings.admin_api_token = "test-secret"

    try:
        with patch(
            "app.api.admin_routes.review_noor_request",
            new_callable=AsyncMock,
            return_value=reviewed,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.patch(
                    f"/v1/admin/noor-requests/{request_id}",
                    json={"status": "approved", "reviewed_by": "concierge@aueshah.com"},
                    headers={"X-Admin-Token": "test-secret"},
                )
    finally:
        settings.admin_api_token = original_token
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["reference_id"] == "NOR-DEADBEEF"
    assert body["cooldown_until"] is not None
