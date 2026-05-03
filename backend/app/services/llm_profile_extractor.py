"""LLM-based profile fact extraction.

Replaces the rigid regex extractor. Given the latest user message and the
client's existing facts, asks a small LLM call to merge any new facts into
the profile and return the updated dict.

Stored as JSONB on `users.profile_facts`. Free-form keys — the agent decides
what's worth remembering. Common keys include:
  - name, age, location
  - looking_for (e.g. "engagement ring for my fiancée")
  - budget, preferred_currency
  - style, skin_tone, metal_preference
  - occasion, deadline
  - notes (free-form)
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from openai import AsyncOpenAI

from app.config.settings import settings

logger = logging.getLogger(__name__)

_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


_SYSTEM_PROMPT = """You extract durable facts about a luxury jewelry client from chat messages.

Given:
  - the client's existing facts (a JSON object)
  - the client's latest message

Return a JSON object representing the UPDATED facts. Rules:

1. Merge new info into the existing facts. Don't drop existing keys unless the
   client explicitly contradicts them (e.g. "actually my budget is now 50k").
2. Only record facts the client states or strongly implies. Don't invent.
3. Use natural keys: name, age, location, looking_for, occasion, budget,
   currency, style, skin_tone, metal_preference, deadline, notes, etc.
4. Values should be concise. Numbers as numbers. Strings short.
5. If the message contains nothing personal, return the existing facts unchanged.
6. Respond with ONLY a JSON object — no prose, no code fences."""


async def extract_and_merge(
    message: str,
    existing_facts: dict,
) -> dict:
    """Run the LLM extraction. Returns the new merged facts dict.

    Failures fall back to the existing facts unchanged. Never raises.
    """
    if not message or not message.strip():
        return existing_facts or {}

    try:
        client = _get_client()
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            max_tokens=500,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Existing facts:\n{json.dumps(existing_facts or {}, ensure_ascii=False)}\n\n"
                        f"Client message:\n{message}\n\n"
                        "Return the updated facts JSON."
                    ),
                },
            ],
            timeout=8.0,
        )
        raw = (resp.choices[0].message.content or "").strip()
        if not raw:
            return existing_facts or {}
        new_facts = json.loads(raw)
        if not isinstance(new_facts, dict):
            return existing_facts or {}
        # Strip any obviously empty values
        cleaned = {k: v for k, v in new_facts.items() if v not in (None, "", [], {})}
        return cleaned
    except Exception as e:
        logger.warning("LLM profile extraction failed: %s", e)
        return existing_facts or {}
