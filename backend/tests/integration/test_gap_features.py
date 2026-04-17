"""Tests for the 7 client-requirements gaps (page context, submit_noor_request tool,
decline cooldown, closure at 143, prompt clauses, selective memory, config tweaks)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# ─── Gap 1: Page-context awareness ──────────────────────────────────

@pytest.mark.asyncio
async def test_page_context_injected_into_orchestrator():
    """ChatRequest with page_context → orchestrator receives PAGE AWARENESS line."""
    from app.api import routes as routes_mod
    from app.main import app
    from app.models.schemas import ChatResponse

    captured: dict = {}

    async def _handle(self, request, *, personalization_preamble=None, **kwargs):  # noqa: ARG001
        captured["page_context_line"] = kwargs.get("page_context_line")
        return ChatResponse(reply="ok", metadata={"intent": "product", "skill": "product"})

    with patch.object(routes_mod.Orchestrator, "handle_chat", new=_handle), \
         patch("app.api.routes.persist_turn", new_callable=AsyncMock):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/chat", json={
                "message": "tell me about this ring",
                "page_context": {
                    "page_type": "product",
                    "product_name": "Celestial Band",
                    "collection_name": "Heritage",
                },
            })

    assert resp.status_code == 200
    line = captured.get("page_context_line")
    assert line is not None
    assert "product page" in line
    assert "Celestial Band" in line
    assert "Heritage" in line


@pytest.mark.asyncio
async def test_page_context_optional():
    """ChatRequest without page_context → no PAGE AWARENESS line."""
    from app.api import routes as routes_mod
    from app.main import app
    from app.models.schemas import ChatResponse

    captured: dict = {}

    async def _handle(self, request, *, personalization_preamble=None, **kwargs):  # noqa: ARG001
        captured["page_context_line"] = kwargs.get("page_context_line")
        return ChatResponse(reply="ok", metadata={"intent": "general", "skill": "general"})

    with patch.object(routes_mod.Orchestrator, "handle_chat", new=_handle), \
         patch("app.api.routes.persist_turn", new_callable=AsyncMock):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/chat", json={"message": "hello"})

    assert resp.status_code == 200
    assert captured.get("page_context_line") is None


# ─── Gap 3: Decline cooldown ────────────────────────────────────────

@pytest.mark.asyncio
async def test_declined_user_blocked_during_cooldown():
    """Declined request with cooldown_until in the future → user_has_active returns it."""
    from app.db.repositories import noor_requests as noor_repo

    future = datetime.now(timezone.utc) + timedelta(days=300)
    declined_row = MagicMock()
    declined_row.status = "declined"
    declined_row.cooldown_until = future
    declined_row.submitted_at = datetime.now(timezone.utc) - timedelta(days=30)

    session = MagicMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = declined_row
    session.execute = AsyncMock(return_value=result_mock)

    blocking = await noor_repo.user_has_active(session, uuid.uuid4())
    assert blocking is not None
    assert blocking.status == "declined"


# ─── Gap 4: Closure at 143 ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_count_approved_repo():
    """count_approved returns scalar count of approved Noor requests."""
    from app.db.repositories import noor_requests as noor_repo

    session = MagicMock()
    result_mock = MagicMock()
    result_mock.scalar_one.return_value = 42
    session.execute = AsyncMock(return_value=result_mock)

    count = await noor_repo.count_approved(session)
    assert count == 42


# ─── Gap 5: Prompt clauses ──────────────────────────────────────────

def test_system_prompt_contains_new_clauses():
    """The system prompt must contain the new brand-brain rules."""
    from app.config.prompts import SYSTEM_PROMPT

    assert "Never invent symbolism" in SYSTEM_PROMPT
    assert "Blog articles" in SYSTEM_PROMPT
    assert "ALLOCATION PROTOCOL" in SYSTEM_PROMPT
    assert "REJECTION & APPROVAL PHILOSOPHY" in SYSTEM_PROMPT


# ─── Gap 6: Selective return memory ─────────────────────────────────

def test_selective_memory_no_qualifying_intent():
    """Personalization preamble returns None if user has no Noor/Bespoke history."""
    from app.core.personalization import build_preamble

    user = MagicMock()
    user.display_name = "Client"
    user.age_range = "30s"
    user.skin_tone = "cool"
    user.style_preference = "modern"
    user.preferred_collection = None
    user.favorite_metals = None
    user.favorite_styles = None

    general_msg = MagicMock()
    general_msg.role = "user"
    general_msg.content = "Hello"
    general_msg.intent = "general"
    general_msg.created_at = datetime.now(timezone.utc)

    result = build_preamble(user, recent_messages=[general_msg], last_intent="general")
    assert result is None


def test_selective_memory_with_noor_intent():
    """Personalization preamble fires when user has Noor history."""
    from app.core.personalization import build_preamble

    user = MagicMock()
    user.display_name = "Client"
    user.age_range = "30s"
    user.skin_tone = "cool"
    user.style_preference = "modern"
    user.preferred_collection = None
    user.favorite_metals = None
    user.favorite_styles = None

    noor_msg = MagicMock()
    noor_msg.role = "user"
    noor_msg.content = "Tell me about Noor"
    noor_msg.intent = "noor"
    noor_msg.created_at = datetime.now(timezone.utc)

    result = build_preamble(user, recent_messages=[noor_msg], last_intent="noor")
    assert result is not None
    assert "30s" in result


def test_selective_memory_expired_noor():
    """Noor interaction older than 30 days does not trigger preamble."""
    from app.core.personalization import build_preamble

    user = MagicMock()
    user.display_name = "Client"
    user.age_range = "30s"
    user.skin_tone = "cool"
    user.style_preference = "modern"
    user.preferred_collection = None
    user.favorite_metals = None
    user.favorite_styles = None

    old_msg = MagicMock()
    old_msg.role = "user"
    old_msg.content = "Noor?"
    old_msg.intent = "noor"
    old_msg.created_at = datetime.now(timezone.utc) - timedelta(days=45)

    result = build_preamble(user, recent_messages=[old_msg], last_intent="general")
    assert result is None


# ─── Gap 7: Config tweaks ───────────────────────────────────────────

def test_timeout_default_is_15():
    from app.config.settings import Settings
    s = Settings(openai_api_key="test-key")
    assert s.request_timeout_seconds == 15


def test_noor_cooldown_default_is_365():
    from app.config.settings import Settings
    s = Settings(openai_api_key="test-key")
    assert s.noor_cooldown_days == 365


def test_noor_max_allocations_default_is_143():
    from app.config.settings import Settings
    s = Settings(openai_api_key="test-key")
    assert s.noor_max_allocations == 143


def test_tokens_used_metric_exists():
    from app.utils.metrics import TOKENS_USED_TOTAL
    assert TOKENS_USED_TOTAL is not None
    TOKENS_USED_TOTAL.labels(type="prompt").inc(0)
    TOKENS_USED_TOTAL.labels(type="completion").inc(0)
