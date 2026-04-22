"""T194-T197: Integration tests for appointment persistence + notifications (Group F)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


def _build_appointment(**overrides):
    base = dict(
        id=uuid.uuid4(),
        reference_id="APT-12345678",
        user_id=None,
        email="client@example.com",
        phone=None,
        appointment_type="virtual",
        preferred_date=None,
        notes=None,
        status="pending",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    base.update(overrides)
    row = MagicMock()
    for k, v in base.items():
        setattr(row, k, v)
    return row


def _valid_payload():
    return {
        "email": "client@example.com",
        "appointment_type": "virtual",
        "phone": "+44 7000 000000",
        "preferred_date": "2026-05-01 14:00 GMT",
        "notes": "Interested in the Empire Allegiance collection.",
    }


# ─── T194: persists row + returns its reference id ─────────────────

@pytest.mark.asyncio
async def test_appointment_persists_to_db():
    from app.db.session import get_session
    from app.main import app

    inserted = _build_appointment(reference_id="APT-AAAA1111")
    notif_capture = MagicMock()

    async def _session_override():
        yield MagicMock()

    app.dependency_overrides[get_session] = _session_override

    try:
        with patch(
            "app.services.appointment_workflow.appt_repo.create",
            new_callable=AsyncMock,
            return_value=inserted,
        ), patch(
            "app.services.appointment_workflow._fire_notifications",
            new=AsyncMock(side_effect=lambda *a, **kw: notif_capture(*a, **kw)),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/appointment-request", json=_valid_payload())
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["reference_id"] == "APT-AAAA1111"
    assert "concierge" in body["message"].lower()


# ─── T195: notifications scheduled via fire-and-forget task ────────

@pytest.mark.asyncio
async def test_notifications_scheduled_after_persist():
    from app.db.session import get_session
    from app.main import app

    inserted = _build_appointment()

    async def _session_override():
        yield MagicMock()

    app.dependency_overrides[get_session] = _session_override

    notif_called = {}

    async def _fake_fire(row, *, user_id):
        notif_called["row"] = row
        notif_called["user_id"] = user_id

    try:
        with patch(
            "app.services.appointment_workflow.appt_repo.create",
            new_callable=AsyncMock,
            return_value=inserted,
        ), patch(
            "app.services.appointment_workflow._fire_notifications",
            new=_fake_fire,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/appointment-request", json=_valid_payload())

            # Yield to the event loop so the create_task body runs.
            import asyncio
            await asyncio.sleep(0)
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    assert notif_called.get("row") is inserted
    assert notif_called.get("user_id") is None


# ─── T196: graceful fallback when DB is not configured ─────────────

@pytest.mark.asyncio
async def test_appointment_falls_back_when_db_unavailable():
    from app.db.session import get_session
    from app.main import app

    async def _session_override():
        yield None

    app.dependency_overrides[get_session] = _session_override

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/appointment-request", json=_valid_payload())
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["reference_id"].startswith("APT-")
    # No DB row means the ID came from the inline fallback path.
    assert len(body["reference_id"]) == 12


# ─── T197: invalid email rejected by Pydantic, never reaches workflow

@pytest.mark.asyncio
async def test_invalid_email_returns_validation_error():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/appointment-request",
            json={"email": "not-an-email", "appointment_type": "virtual"},
        )

    # FastAPI returns 422 for body validation failures.
    assert resp.status_code == 422


# ─── Workflow notification fan-out (sanity) ────────────────────────

@pytest.mark.asyncio
async def test_workflow_fans_out_email_notifications():
    """`_fire_notifications` schedules both the client and concierge emails."""
    from app.services import appointment_workflow

    row = _build_appointment(email="x@y.com")

    with patch(
        "app.services.appointment_workflow.email_notifier.send_client_appointment_confirmation",
        new_callable=AsyncMock,
    ) as m_client, patch(
        "app.services.appointment_workflow.email_notifier.send_concierge_appointment_alert",
        new_callable=AsyncMock,
    ) as m_concierge:
        await appointment_workflow._fire_notifications(row, user_id=None)

    m_client.assert_awaited_once()
    m_concierge.assert_awaited_once()
