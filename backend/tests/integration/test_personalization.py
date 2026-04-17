"""T160-T162: Integration tests for personalization (Group D).

These tests assert the wiring contract between /chat, the optional auth
dependency, the personalization preamble, and the orchestrator. They mock the
Agents SDK runner to capture the input_items it receives.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


def _build_user(**overrides):
    """A minimal User-like object the route + preamble builder can read."""
    base = dict(
        id=uuid.uuid4(),
        wp_user_id=99,
        email="returning@example.com",
        display_name="Returning Client",
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


def _chat_msg(role: str, content: str, intent: str | None = None):
    m = MagicMock()
    m.role = role
    m.content = content
    m.intent = intent
    m.created_at = datetime.now(timezone.utc)
    return m


def _orchestrator_capturing_input():
    """Patches the Orchestrator so handle_chat returns a canned ChatResponse
    and exposes the personalization_preamble it received."""
    from app.models.schemas import ChatResponse

    captured: dict = {}

    async def _handle_chat(self, request, *, personalization_preamble=None, **kwargs):
        captured["preamble"] = personalization_preamble
        captured["message"] = request.message
        return ChatResponse(
            reply="ok",
            metadata={"intent": "general", "skill": "general", "routing_source": "agents_sdk", "latency_ms": 5},
        )

    return captured, _handle_chat


@pytest.mark.asyncio
async def test_returning_user_greeted_with_context():
    """T160: Authenticated user with prior Noor history → preamble references Noor."""
    from app.api import routes as routes_mod
    from app.auth.dependencies import get_current_user_optional
    from app.main import app
    from app.services.summary_cache import get_summary_cache

    get_summary_cache().clear()
    user = _build_user()
    captured, handle_chat = _orchestrator_capturing_input()

    recent = [
        _chat_msg("user", "Tell me about the Noor Collection"),
        _chat_msg("assistant", "The Noor Collection is our limited 143-piece edition...", intent="noor"),
    ]

    fake_factory = MagicMock()
    fake_session = MagicMock()
    fake_factory.return_value.__aenter__ = AsyncMock(return_value=fake_session)
    fake_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    app.dependency_overrides[get_current_user_optional] = lambda: user
    try:
        with patch.object(routes_mod.Orchestrator, "handle_chat", new=handle_chat), \
             patch("app.api.routes.get_session_factory", return_value=fake_factory), \
             patch("app.api.routes.chat_repo.get_recent_for_user", new_callable=AsyncMock, return_value=recent), \
             patch("app.api.routes.chat_repo.get_last_intent", new_callable=AsyncMock, return_value="noor"), \
             patch("app.api.routes.persist_turn", new_callable=AsyncMock):

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/chat", json={"message": "hi"})
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)

    assert resp.status_code == 200
    assert captured["preamble"] is not None
    assert "Noor" in captured["preamble"]
    assert "Last intent: noor" in captured["preamble"]


@pytest.mark.asyncio
async def test_profile_injected_when_available():
    """T161: User with skin_tone + style → preamble carries those fields."""
    from app.api import routes as routes_mod
    from app.auth.dependencies import get_current_user_optional
    from app.main import app
    from app.services.summary_cache import get_summary_cache

    get_summary_cache().clear()
    user = _build_user(skin_tone="cool", style_preference="heritage", age_range="40s")
    captured, handle_chat = _orchestrator_capturing_input()

    fake_factory = MagicMock()
    fake_session = MagicMock()
    fake_factory.return_value.__aenter__ = AsyncMock(return_value=fake_session)
    fake_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    recent = [
        _chat_msg("user", "I'd like a custom piece", intent="bespoke"),
    ]

    app.dependency_overrides[get_current_user_optional] = lambda: user
    try:
        with patch.object(routes_mod.Orchestrator, "handle_chat", new=handle_chat), \
             patch("app.api.routes.get_session_factory", return_value=fake_factory), \
             patch("app.api.routes.chat_repo.get_recent_for_user", new_callable=AsyncMock, return_value=recent), \
             patch("app.api.routes.chat_repo.get_last_intent", new_callable=AsyncMock, return_value="bespoke"), \
             patch("app.api.routes.persist_turn", new_callable=AsyncMock):

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/chat", json={"message": "show me something"})
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)

    assert resp.status_code == 200
    preamble = captured["preamble"]
    assert preamble is not None
    assert "cool" in preamble
    assert "heritage" in preamble
    assert "40s" in preamble


@pytest.mark.asyncio
async def test_anonymous_unchanged():
    """T162: Anonymous request → no preamble passed to orchestrator."""
    from app.api import routes as routes_mod
    from app.main import app

    captured, handle_chat = _orchestrator_capturing_input()

    with patch.object(routes_mod.Orchestrator, "handle_chat", new=handle_chat), \
         patch("app.api.routes.persist_turn", new_callable=AsyncMock):

        # No dependency override — get_current_user_optional naturally returns None
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/chat", json={"message": "hello"})

    assert resp.status_code == 200
    assert captured["preamble"] is None
