"""T201: Chaos — system stays brand-safe when each external dependency fails.

Each test simulates one degradation and asserts the response is either a
2xx fallback or a typed envelope — never a 500 with internals leaked.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# ─── 1. Redis down → rate limiter fails open ───────────────────────

@pytest.mark.asyncio
async def test_redis_down_fail_open_allows_chat():
    """Rate limiter must NOT block traffic when Redis is unreachable."""
    from app.api import routes as routes_mod
    from app.main import app
    from app.middleware import rate_limiter as rl
    from app.models.schemas import ChatResponse

    async def _handle(self, request, *, personalization_preamble=None, **kwargs):  # noqa: ARG001
        return ChatResponse(reply="ok", metadata={})

    fake_client = MagicMock()
    fake_pipe = MagicMock()
    fake_pipe.zremrangebyscore = MagicMock(return_value=fake_pipe)
    fake_pipe.zadd = MagicMock(return_value=fake_pipe)
    fake_pipe.zcard = MagicMock(return_value=fake_pipe)
    fake_pipe.expire = MagicMock(return_value=fake_pipe)
    fake_pipe.execute = AsyncMock(side_effect=ConnectionError("Redis unreachable"))
    fake_client.pipeline = MagicMock(return_value=fake_pipe)

    with patch.object(rl, "get_redis_client", return_value=fake_client), patch.object(
        routes_mod.Orchestrator, "handle_chat", new=_handle
    ), patch("app.api.routes.persist_turn", new_callable=AsyncMock):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/chat", json={"message": "hello"})

    assert resp.status_code == 200
    assert resp.json()["reply"] == "ok"


# ─── 2. Neon DB down → chat still answers, persistence skipped ─────

@pytest.mark.asyncio
async def test_neon_down_chat_still_answers():
    """Persistence layer must swallow DB errors — request path stays open."""
    from app.api import routes as routes_mod
    from app.main import app
    from app.models.schemas import ChatResponse

    async def _handle(self, request, *, personalization_preamble=None, **kwargs):  # noqa: ARG001
        return ChatResponse(reply="we're here", metadata={})

    persist_mock = AsyncMock(side_effect=Exception("Neon connection refused"))
    with patch.object(routes_mod.Orchestrator, "handle_chat", new=_handle), patch(
        "app.api.routes.persist_turn", new=persist_mock
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/chat", json={"message": "hi"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "we're here"


# ─── 3. OpenAI / agents SDK timeout → typed 503 envelope ───────────

@pytest.mark.asyncio
async def test_openai_timeout_returns_brand_safe_fallback():
    from app.api import routes as routes_mod
    from app.main import app
    from app.models.errors import AITimeout

    async def _handle(self, request, *, personalization_preamble=None, **kwargs):  # noqa: ARG001
        raise AITimeout()

    with patch.object(routes_mod.Orchestrator, "handle_chat", new=_handle), patch(
        "app.api.routes.persist_turn", new_callable=AsyncMock
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/chat", json={"message": "tell me about Noor"})

    assert resp.status_code == 503
    body = resp.json()
    assert "code" in body
    assert "error" in body
    # Brand-safe message (no stack frames, no API names)
    assert "openai" not in body["error"].lower()
    assert "Traceback" not in body["error"]


# ─── 4. Resend 500 → noor request still succeeds ────────────────

@pytest.mark.asyncio
async def test_resend_failure_does_not_break_noor_submission():
    """Notification fan-out is fire-and-forget. Resend failure must not 500."""
    import uuid as _uuid
    from datetime import datetime, timezone
    from app.auth.dependencies import get_current_user
    from app.db.session import get_session
    from app.main import app

    user = MagicMock()
    user.id = _uuid.uuid4()
    user.email = "client@example.com"

    inserted = MagicMock()
    inserted.reference_id = "NOR-CHAOS001"
    inserted.id = _uuid.uuid4()
    inserted.user_id = user.id
    inserted.full_name = "Test Client"
    inserted.purpose = "Test"
    inserted.timeline = "soon"
    inserted.delivery_location = "Earth"
    inserted.contact_method = "email"
    inserted.contact_details = "client@example.com"
    inserted.status = "pending"
    inserted.cooldown_until = None
    inserted.submitted_at = datetime.now(timezone.utc)
    inserted.reviewed_at = None

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
            "app.services.noor_workflow.email_notifier.send_client_noor_confirmation",
            new=AsyncMock(side_effect=Exception("Resend 500")),
        ), patch(
            "app.services.noor_workflow.email_notifier.send_concierge_noor_alert",
            new=AsyncMock(side_effect=Exception("Resend 500")),
        ), patch(
            "app.services.noor_workflow.log_activity",
            new=AsyncMock(),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(
                    "/v1/noor-requests",
                    json={
                        "full_name": "Test Client",
                        "purpose": "A milestone piece",
                        "timeline": "3 months",
                        "delivery_location": "London",
                        "contact_method": "email",
                        "contact_details": "client@example.com",
                    },
                )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 201
    assert resp.json()["reference_id"] == "NOR-CHAOS001"


# ─── 5. Resend 500 on appointment → still succeeds ─────────────

@pytest.mark.asyncio
async def test_resend_failure_does_not_break_appointment():
    from app.db.session import get_session
    from app.main import app
    from datetime import datetime, timezone
    import uuid as _uuid

    inserted = MagicMock()
    inserted.reference_id = "APT-CHAOS01"
    inserted.id = _uuid.uuid4()
    inserted.user_id = None
    inserted.email = "x@y.com"
    inserted.phone = None
    inserted.appointment_type = "virtual"
    inserted.preferred_date = None
    inserted.notes = None
    inserted.status = "pending"
    inserted.created_at = datetime.now(timezone.utc)

    async def _session_override():
        yield MagicMock()

    app.dependency_overrides[get_session] = _session_override

    try:
        with patch(
            "app.services.appointment_workflow.appt_repo.create",
            new_callable=AsyncMock,
            return_value=inserted,
        ), patch(
            "app.services.appointment_workflow.email_notifier.send_client_appointment_confirmation",
            new=AsyncMock(side_effect=Exception("Resend 500")),
        ), patch(
            "app.services.appointment_workflow.email_notifier.send_concierge_appointment_alert",
            new=AsyncMock(side_effect=Exception("Resend 500")),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(
                    "/appointment-request",
                    json={"email": "x@y.com", "appointment_type": "virtual"},
                )
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
