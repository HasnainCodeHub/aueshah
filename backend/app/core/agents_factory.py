"""Aueshah Concierge — Agents SDK wiring.

One triage agent with native handoffs to 5 specialist agents (product, compare,
noor, bespoke, general). Each specialist inherits the shared brand-brain
instructions (Data.txt v2.0) plus its own skill-specific addendum.

RAG is exposed as a function tool; only specialists that benefit from factual
grounding (product, compare) are given access.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from agents import Agent, ModelSettings, function_tool

from app.config.prompts import SKILL_PROMPTS, SYSTEM_PROMPT
from app.config.settings import settings
from app.services.noor_catalog import find_best_noor_pieces
from app.services.rag_service import RAGService
from app.utils.validators import injection_guardrail, off_topic_guardrail

logger = logging.getLogger(__name__)


# ---------- Tools ----------

_rag_service: RAGService | None = None


def _get_rag() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


@function_tool
async def noor_recommend(
    age: int | None = None,
    skin_tone: str | None = None,
    style_preference: str | None = None,
    occasion: str | None = None,
    category: str | None = None,
) -> str:
    """Return up to 2 Noor Collection pieces best matched to the client's profile.

    Call this ONLY after you have collected from the client (a) age or age range,
    (b) skin tone (cool / warm / neutral), and (c) style preference
    (minimalist / statement / heritage / modern). Occasion and category are
    optional refinements.

    Args:
        age: Client age as an integer (use the midpoint of a range if given one).
        skin_tone: "cool", "warm", or "neutral".
        style_preference: "minimalist", "statement", "heritage", or "modern".
        occasion: Free-form tag — "love", "anniversary", "gift", "self_reward",
            "legacy", "milestone", "everyday", "status", "celebration".
        category: Optional — "ring", "bracelet", "pendant", "earrings".

    Returns a short structured block with piece name, category, metal, style,
    description, and narrative line for each match. Use this as your only
    factual source when presenting the piece — do not add details not shown.
    """
    matches = find_best_noor_pieces(
        age=age,
        skin_tone=skin_tone,
        style_preference=style_preference,
        occasion=occasion,
        category=category,
        top_k=2,
    )
    if not matches:
        return "(no Noor matches available — offer to connect the client with our private concierge)"
    lines = []
    for p in matches:
        lines.append(
            f"- {p['name']} ({p['category']}, {p['metal']}, {p['style']}): "
            f"{p['description']} — {p['narrative']}"
        )
    return "\n".join(lines)


@function_tool
async def search_catalog(query: str) -> str:
    """Search the Aueshah catalog and heritage knowledge base for grounded facts
    about specific pieces, materials, stones, collections, or policies.

    Call this ONLY when you need concrete factual detail (e.g., a piece's
    material, a specific collection's story, policy text). Do not call it for
    general brand conversation. Returns a short bulleted context block. If
    nothing relevant is found, returns an empty-result marker — in that case,
    honestly tell the client you'll confirm the detail with the atelier.

    Args:
        query: A focused query describing exactly what factual info you need.
    """
    if not settings.enable_rag:
        return "(catalog lookup disabled)"

    try:
        rag = _get_rag()
        embedding = await rag.get_embeddings(query)
        if not embedding:
            return "(no catalog results)"
        chunks = await rag.retrieve(embedding, top_k=3)
        if not chunks:
            return "(no catalog results)"
        lines = []
        for c in chunks:
            src = f" [source: {c.source}]" if c.source else ""
            lines.append(f"- {c.content}{src}")
        return "\n".join(lines)
    except Exception as e:  # graceful degradation — never fail the turn
        logger.warning(f"search_catalog tool failed: {e}")
        return "(catalog lookup unavailable)"


# ---------- Instruction helpers ----------

def _specialist_instructions(skill_key: str) -> str:
    """Compose full instructions: brand brain + skill-specific addendum."""
    skill_body = SKILL_PROMPTS[skill_key]
    return f"{SYSTEM_PROMPT}\n\n—————————————————————————————\nACTIVE SKILL: {skill_key.upper()}\n—————————————————————————————\n{skill_body}"


# ---------- Agents ----------

@lru_cache(maxsize=1)
def build_triage_agent() -> Agent:
    """Build the triage agent with handoffs to all 5 specialists.

    Cached — built once per process. The triage agent's only job is to read the
    client's message and route to the right specialist. It never replies on its
    own except to route.
    """
    model = settings.openai_model
    model_settings = ModelSettings(temperature=0.4)

    product_agent = Agent(
        name="product",
        handoff_description="Present a specific Aueshah piece or recommend pieces from our collections (rings, bracelets, earrings, pendants, necklaces, tiaras, waist adornments).",
        instructions=_specialist_instructions("product"),
        model=model,
        model_settings=model_settings,
        tools=[search_catalog],
    )

    compare_agent = Agent(
        name="compare",
        handoff_description="Compare two specific Aueshah pieces side by side, framing distinctions as fit (not winner vs loser).",
        instructions=_specialist_instructions("compare"),
        model=model,
        model_settings=model_settings,
        tools=[search_catalog],
    )

    noor_agent = Agent(
        name="noor",
        handoff_description="Handle inquiries about the Noor Collection — our limited 143-piece private edition. Profile the client (age, skin tone, preference) and recommend a matching Noor piece using the noor_recommend tool, then invite a private concierge introduction.",
        instructions=_specialist_instructions("noor"),
        model=model,
        model_settings=model_settings,
        tools=[noor_recommend],
    )

    bespoke_agent = Agent(
        name="bespoke",
        handoff_description="Handle custom, made-to-order, one-of-a-kind design requests. Route warmly to our atelier.",
        instructions=_specialist_instructions("bespoke"),
        model=model,
        model_settings=model_settings,
    )

    general_agent = Agent(
        name="general",
        handoff_description="Handle brand heritage, philosophy, ethical sourcing, appointments, repairs, warranty, sizing, care, and any other non-piece questions. This is the default fallback.",
        instructions=_specialist_instructions("general"),
        model=model,
        model_settings=model_settings,
    )

    triage_agent = Agent(
        name="triage",
        instructions=(
            "You are the silent routing layer of the Aueshah Concierge.\n"
            "Your ONLY job is to read the client's latest message and hand off "
            "to the most appropriate specialist. You do not write replies yourself.\n\n"
            "HANDOFF RULES (apply in order):\n"
            "1. If the message mentions the Noor Collection by name → hand off to `noor`.\n"
            "2. If the message is about custom/bespoke/made-to-order design → hand off to `bespoke`.\n"
            "3. If the message compares two or more specific pieces → hand off to `compare`.\n"
            "4. If the message asks about a specific piece, collection, material, or recommendation → hand off to `product`.\n"
            "5. Otherwise (greetings, brand questions, appointments, policies, care, heritage, anything unclear) → hand off to `general`.\n\n"
            "When in doubt, prefer `general`. Never reply directly — always hand off."
        ),
        model=model,
        model_settings=ModelSettings(temperature=0.0),
        handoffs=[noor_agent, bespoke_agent, compare_agent, product_agent, general_agent],
        input_guardrails=[injection_guardrail, off_topic_guardrail],
    )

    return triage_agent
