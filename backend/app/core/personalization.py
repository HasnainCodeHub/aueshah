"""T164: Personalization preamble builder.

Produces a compact prompt block that the orchestrator prepends ahead of the
brand-brain system prompt for authenticated, returning users. The preamble
captures three things the model needs to feel like it remembers the client:

  1. Known profile fields (age range, skin tone, style preference, ...).
  2. The last intent / skill the client engaged with.
  3. A short summary of the most recent turns (what was discussed).

The preamble is intentionally short (target ≤400 tokens) and never duplicates
brand-brain content — it's pure per-user context.

Return-visitor memory only triggers when the user previously engaged with
Noor allocation or Bespoke consultation, and auto-expires (Noor: 30 days,
Bespoke: 60 days from last interaction).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from app.db.models import ChatMessage, User

MAX_SUMMARY_MESSAGES = 20
MAX_SUMMARY_CHARS = 2400
NOOR_MEMORY_EXPIRY_DAYS = 30
BESPOKE_MEMORY_EXPIRY_DAYS = 60
MEMORY_TRIGGERING_INTENTS = {"noor", "bespoke"}


def _profile_block(user: User) -> Optional[str]:
    """Build the profile block. Display name alone doesn't count — we only
    surface the block when the user has shared at least one substantive
    preference."""
    substantive: list[str] = []
    if user.age_range:
        substantive.append(f"Age range: {user.age_range}")
    if user.skin_tone:
        substantive.append(f"Skin tone: {user.skin_tone}")
    if user.style_preference:
        substantive.append(f"Style preference: {user.style_preference}")
    if user.preferred_collection:
        substantive.append(f"Preferred collection: {user.preferred_collection}")
    if user.favorite_metals:
        substantive.append(f"Favorite metals: {', '.join(user.favorite_metals)}")
    if user.favorite_styles:
        substantive.append(f"Favorite styles: {', '.join(user.favorite_styles)}")

    if not substantive:
        return None

    fields: list[str] = []
    if user.display_name:
        fields.append(f"Name: {user.display_name}")
    fields.extend(substantive)
    return "Known profile:\n" + "\n".join(f"  - {f}" for f in fields)


def summarize_recent(messages: Iterable[ChatMessage]) -> Optional[str]:
    """Compact summary of the last few turns, capped to MAX_SUMMARY_CHARS."""
    msgs = [m for m in messages if m.role in ("user", "assistant")]
    if not msgs:
        return None
    msgs = msgs[-MAX_SUMMARY_MESSAGES:]
    lines: list[str] = []
    for m in msgs:
        snippet = (m.content or "").strip().replace("\n", " ")
        if len(snippet) > 200:
            snippet = snippet[:197] + "..."
        prefix = "Client" if m.role == "user" else "Concierge"
        lines.append(f"  - {prefix}: {snippet}")
    body = "\n".join(lines)
    if len(body) > MAX_SUMMARY_CHARS:
        body = body[:MAX_SUMMARY_CHARS - 3] + "..."
    return "Recent exchange:\n" + body


def _has_qualifying_interaction(
    recent_messages: list[ChatMessage],
    last_intent: Optional[str],
) -> bool:
    """Return True if the user previously engaged with Noor or Bespoke within
    their respective expiry windows."""
    if last_intent in MEMORY_TRIGGERING_INTENTS:
        return True
    now = datetime.now(timezone.utc)
    for msg in recent_messages:
        intent = getattr(msg, "intent", None)
        if intent not in MEMORY_TRIGGERING_INTENTS:
            continue
        created = getattr(msg, "created_at", None)
        if created is None:
            continue
        if intent == "noor" and (now - created) <= timedelta(days=NOOR_MEMORY_EXPIRY_DAYS):
            return True
        if intent == "bespoke" and (now - created) <= timedelta(days=BESPOKE_MEMORY_EXPIRY_DAYS):
            return True
    return False


def _facts_block(user: User) -> Optional[str]:
    """Render the JSONB profile_facts as a readable block."""
    facts = getattr(user, "profile_facts", None) or {}
    if not isinstance(facts, dict) or not facts:
        return None
    lines: list[str] = []
    for k, v in facts.items():
        if v in (None, "", [], {}):
            continue
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        key = k.replace("_", " ").title()
        lines.append(f"  - {key}: {v}")
    if not lines:
        return None
    return "Known facts:\n" + "\n".join(lines)


def build_preamble(
    user: Optional[User],
    recent_messages: Optional[list[ChatMessage]] = None,
    last_intent: Optional[str] = None,
) -> Optional[str]:
    """Assemble the full per-user preamble for an authenticated user.

    Always returns a preamble for any authenticated user — at minimum the
    name, plus whatever facts and recent history we have.
    """
    if user is None:
        return None

    msgs = recent_messages or []
    sections: list[str] = []
    sections.append(
        "RETURNING-CLIENT CONTEXT (use silently — never recite the profile back verbatim, "
        "but let it shape your tone, recommendations, and what you reference). "
        "Address the client by name when natural; weave in their stated preferences, "
        "budget, occasion, and prior interest without making them repeat themselves."
    )

    # Identity line — always present for authenticated users
    name = (user.display_name or "").strip()
    if name:
        sections.append(f"Client identity: {name} (email: {user.email})")

    facts = _facts_block(user)
    if facts:
        sections.append(facts)

    profile = _profile_block(user)
    if profile:
        sections.append(profile)

    if last_intent and last_intent not in {"general", "off_topic", None}:
        sections.append(f"Last intent: {last_intent}")

    summary = summarize_recent(msgs)
    if summary:
        sections.append(summary)

    if len(sections) == 1:
        return None

    return "\n\n".join(sections)
