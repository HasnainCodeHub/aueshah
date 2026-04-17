"""T163: Unit tests for the personalization preamble + summary builder."""
import uuid
from datetime import datetime, timezone

import pytest

from app.core.personalization import (
    MAX_SUMMARY_MESSAGES,
    build_preamble,
    summarize_recent,
)
from app.db.models import ChatMessage, User


def _user(**overrides) -> User:
    base = dict(
        id=uuid.uuid4(),
        wp_user_id=42,
        email="client@example.com",
        display_name="Test Client",
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
    u = User()
    for k, v in base.items():
        setattr(u, k, v)
    return u


def _msg(role: str, content: str, intent: str | None = None) -> ChatMessage:
    m = ChatMessage()
    m.id = uuid.uuid4()
    m.user_id = uuid.uuid4()
    m.visitor_id = uuid.uuid4()
    m.session_id = uuid.uuid4()
    m.role = role
    m.content = content
    m.intent = intent
    m.skill = None
    m.routing_source = None
    m.latency_ms = None
    m.rag_chunk_ids = []
    m.created_at = datetime.now(timezone.utc)
    return m


def test_summarize_recent_caps_to_max_messages():
    msgs = [_msg("user" if i % 2 == 0 else "assistant", f"msg {i}") for i in range(20)]
    out = summarize_recent(msgs)
    assert out is not None
    assert out.count("\n  - ") == MAX_SUMMARY_MESSAGES
    assert "msg 19" in out  # most recent kept


def test_summarize_recent_returns_none_for_empty():
    assert summarize_recent([]) is None


def test_summarize_recent_truncates_long_lines():
    long = "x" * 500
    out = summarize_recent([_msg("user", long)])
    assert out is not None
    assert "..." in out


def test_build_preamble_returns_none_for_anonymous():
    assert build_preamble(None) is None


def test_build_preamble_returns_none_when_no_personal_data():
    """A returning user with empty profile and no history yields no preamble."""
    user = _user()
    assert build_preamble(user, recent_messages=[], last_intent=None) is None


def test_build_preamble_includes_profile_fields():
    user = _user(age_range="30s", skin_tone="cool", style_preference="heritage")
    recent = [_msg("user", "I'd like a bespoke piece", intent="bespoke")]
    preamble = build_preamble(user, recent_messages=recent, last_intent="bespoke")
    assert preamble is not None
    assert "30s" in preamble
    assert "cool" in preamble
    assert "heritage" in preamble


def test_build_preamble_includes_last_intent_when_meaningful():
    user = _user()
    preamble = build_preamble(user, recent_messages=[], last_intent="noor")
    assert preamble is not None
    assert "noor" in preamble


def test_build_preamble_skips_generic_last_intent():
    user = _user(age_range="40s")
    recent = [_msg("user", "Tell me about Noor", intent="noor")]
    preamble = build_preamble(user, recent_messages=recent, last_intent="general")
    assert preamble is not None
    assert "Last intent" not in preamble


def test_build_preamble_returns_none_without_qualifying_intent():
    """Personalization only triggers for users who previously engaged with Noor or Bespoke."""
    user = _user(age_range="30s", skin_tone="cool")
    recent = [_msg("user", "Hello", intent="general")]
    assert build_preamble(user, recent_messages=recent, last_intent="general") is None


def test_build_preamble_includes_recent_summary():
    user = _user()
    msgs = [
        _msg("user", "Tell me about the Noor Collection"),
        _msg("assistant", "The Noor Collection is a limited 143-piece edition..."),
    ]
    preamble = build_preamble(user, recent_messages=msgs, last_intent="noor")
    assert preamble is not None
    assert "Noor" in preamble
