"""T202: End-to-end client journey (mocked DB + AI).

Validates the cross-feature contract — chat → personalization → noor → admin
review — without requiring live external services. Uses dependency overrides
and patched repositories so the journey is deterministic.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# ─── Fixtures ─────────────────────────────────────────────────────

def _build_user(**overrides):
    base = dict(
        id=uuid.uuid4(),
        wp_user_id=99,
        email="journey@example.com",
        display_name="Journey Client",
        age_range=None,
        skin_tone=None,
        style_preference=None,
        preferred_collection=None,
        favorite_metals=None,
        favorite_styles=None,
        role="client",
        status="active",
        created_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    base.update(overrides)
    user = MagicMock()
    for k, v in base.items():
        setattr(user, k, v)
    return user


def _build_noor_row(user_id, *, status="pending", cooldown_until=None):
    now = datetime.now(timezone.utc)
    row = MagicMock()
    row.id = uuid.uuid4()
    row.reference_id = "NOR-JOURNEY1"
    row.user_id = user_id
    row.full_name = "Journey Client"
    row.purpose = "A keepsake for a milestone"
    row.timeline = "3 months"
    row.delivery_location = "London"
    row.contact_method = "email"
    row.contact_details = "journey@example.com"
    row.status = status
    row.cooldown_until = cooldown_until
    row.submitted_at = now
    row.reviewed_at = None
    row.reviewed_by = None
    return row


# ─── Single end-to-end test ────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_journey_chat_login_noor_admin_personalized():
    from app.api import routes as routes_mod
    from app.auth.dependencies import get_current_user, get_current_user_optional
    from app.config.settings import settings
    from app.db.session import get_session
    from app.main import app
    from app.models.schemas import ChatResponse
    from app.services.summary_cache import get_summary_cache

    get_summary_cache().clear()

    # Configure admin token for the admin step.
    original_admin = settings.admin_api_token
    settings.admin_api_token = "journey-secret"

    user = _build_user()
    noor_row = _build_noor_row(user.id)

    # ── Step 1: anonymous chat ─────────────────────────────────────
    captured: dict = {}

    async def _handle(self, request, *, personalization_preamble=None, **kwargs):  # noqa: ARG001
        captured["preamble"] = personalization_preamble
        captured["message"] = request.message
        return ChatResponse(reply="Hi, lovely to have you with us.", metadata={"intent": "general", "skill": "general"})

    fake_factory = MagicMock()
    fake_session = MagicMock()
    fake_factory.return_value.__aenter__ = AsyncMock(return_value=fake_session)
    fake_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    async def _session_override():
        yield MagicMock()

    app.dependency_overrides[get_session] = _session_override

    try:
        with patch.object(routes_mod.Orchestrator, "handle_chat", new=_handle), patch(
            "app.api.routes.persist_turn", new_callable=AsyncMock
        ), patch(
            "app.api.routes.get_session_factory", return_value=fake_factory
        ), patch(
            "app.api.routes.chat_repo.get_recent_for_user", new_callable=AsyncMock, return_value=[]
        ), patch(
            "app.api.routes.chat_repo.get_last_intent", new_callable=AsyncMock, return_value=None
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                # ── 1. Anonymous chat
                resp = await ac.post("/chat", json={"message": "hi"})
                assert resp.status_code == 200
                assert captured["preamble"] is None  # no auth = no preamble

                # ── 2. Authenticated chat — preamble must appear
                app.dependency_overrides[get_current_user_optional] = lambda: user
                recent = [
                    MagicMock(role="user", content="Tell me about Noor", intent=None),
                    MagicMock(role="assistant", content="The Noor Collection...", intent="noor"),
                ]
                with patch(
                    "app.api.routes.chat_repo.get_recent_for_user",
                    new_callable=AsyncMock,
                    return_value=recent,
                ), patch(
                    "app.api.routes.chat_repo.get_last_intent",
                    new_callable=AsyncMock,
                    return_value="noor",
                ):
                    resp = await ac.post("/chat", json={"message": "what about Noor?"})
                    assert resp.status_code == 200
                    assert captured["preamble"] is not None
                    assert "Noor" in captured["preamble"]

                # ── 3. Noor allocation submission
                app.dependency_overrides[get_current_user] = lambda: user
                with patch(
                    "app.services.noor_workflow.noor_repo.user_has_active",
                    new_callable=AsyncMock,
                    return_value=None,
                ), patch(
                    "app.services.noor_workflow.noor_repo.create",
                    new_callable=AsyncMock,
                    return_value=noor_row,
                ), patch(
                    "app.services.noor_workflow._fire_notifications_on_create",
                    new_callable=AsyncMock,
                ):
                    resp = await ac.post(
                        "/v1/noor-requests",
                        json={
                            "full_name": "Journey Client",
                            "purpose": "A keepsake for a milestone",
                            "timeline": "3 months",
                            "delivery_location": "London",
                            "contact_method": "email",
                            "contact_details": "journey@example.com",
                        },
                    )
                    assert resp.status_code == 201
                    body = resp.json()
                    assert body["reference_id"] == "NOR-JOURNEY1"

                # ── 4. Admin approves — workflow updates row to approved + cooldown
                approved = _build_noor_row(
                    user.id,
                    status="approved",
                    cooldown_until=datetime.now(timezone.utc),
                )
                approved.reviewed_at = datetime.now(timezone.utc)
                approved.reviewed_by = "concierge@aueshah.com"

                with patch(
                    "app.api.admin_routes.review_noor_request",
                    new_callable=AsyncMock,
                    return_value=approved,
                ):
                    resp = await ac.patch(
                        f"/v1/admin/noor-requests/{noor_row.id}",
                        json={"status": "approved", "reviewed_by": "concierge@aueshah.com"},
                        headers={"X-Admin-Token": "journey-secret"},
                    )
                    assert resp.status_code == 200
                    assert resp.json()["status"] == "approved"

                # ── 5. Returning chat after profile update — preamble reflects state
                user.style_preference = "heritage"
                user.skin_tone = "cool"
                get_summary_cache().clear()  # reset because user object changed
                with patch(
                    "app.api.routes.chat_repo.get_recent_for_user",
                    new_callable=AsyncMock,
                    return_value=recent,
                ), patch(
                    "app.api.routes.chat_repo.get_last_intent",
                    new_callable=AsyncMock,
                    return_value="noor",
                ):
                    resp = await ac.post("/chat", json={"message": "back again"})
                    assert resp.status_code == 200
                    preamble = captured["preamble"]
                    assert preamble is not None
                    assert "heritage" in preamble
                    assert "cool" in preamble

    finally:
        settings.admin_api_token = original_admin
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_user_optional, None)
        app.dependency_overrides.pop(get_session, None)
