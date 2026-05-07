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
from app.db.session import get_session_factory
from app.db.repositories import noor_requests as noor_repo
from app.services.appointment_workflow import create_appointment
from app.services.noor_catalog import find_best_noor_pieces
from app.services.product_catalog import find_best_products
from app.services.rag_service import RAGService
from app.utils.metrics import APPOINTMENT_REQUESTS_TOTAL, NOOR_REQUESTS_TOTAL
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
async def recommend_pieces(
    age: int | None = None,
    skin_tone: str | None = None,
    style_preference: str | None = None,
    occasion: str | None = None,
    category: str | None = None,
    surface_tone: str | None = None,
    face_shape: str | None = None,
    body_shape: str | None = None,
    height_band: str | None = None,
    finger_length: str | None = None,
    birth_month: int | None = None,
    cultural_background: str | None = None,
    personality: str | None = None,
    budget_band: str | None = None,
) -> str:
    """Return three Aueshah pieces matched to the client profile, structured as
    PRIMARY (perfect match), SECONDARY (slight variation), STATEMENT (bolder
    evolution). Use this as your only fact source when presenting non-Noor
    pieces — never invent details.

    ONLY pass the dimensions the client has actually expressed — never guess
    or fill from the piece's name. Missing dimensions degrade gracefully.

    Required minimum: at least one of `skin_tone`, `style_preference`,
    `occasion`, `personality`, `birth_month` (so the matcher has signal).

    Args by axis (all optional):
      - age: client age (int) or midpoint of a stated range.
      - skin_tone (undertone): "cool" / "warm" / "neutral".
      - surface_tone: "fair" / "light" / "medium" / "olive" / "tan" / "deep".
      - style_preference: "minimalist" / "statement" / "heritage" / "modern".
      - occasion: free-form — "engagement", "anniversary", "gift_for_partner",
        "gift_for_mother", "gift_for_friend", "self_purchase", "formal_event",
        "milestone_birthday", "heritage_addition", "love", "legacy", "status".
      - category: "ring", "bracelet", "earrings", "pendant", "necklace",
        "tiara", "waist_adornment".
      - face_shape: relevant for earrings/necklaces — "oval" / "round" /
        "square" / "heart" / "diamond" / "long".
      - body_shape: "petite" / "tall_slim" / "curvy" / "athletic".
      - height_band: "short" / "medium" / "tall".
      - finger_length: relevant for rings — "long" / "short" / "balanced".
      - birth_month: 1-12 (drives birthstone alignment).
      - cultural_background: "middle_eastern" / "south_asian" / "east_asian" /
        "european" / "african" / "american".
      - personality: "minimalist" / "romantic" / "powerful" / "executive" /
        "artistic".
      - budget_band: "entry" / "mid" / "luxury" (gates statement tier).

    Returns a structured PRIMARY / SECONDARY / STATEMENT block. Each pick
    includes a `Reasons` line — short styling rationales (e.g. "warm
    undertone → yellow gold", "long fingers → emerald cut", "May → emerald").
    You may echo at most ONE reason per pick in the client's own voice;
    never invent a reason that isn't listed.
    """
    picks = find_best_products(
        age=age,
        skin_tone=skin_tone,
        style_preference=style_preference,
        occasion=occasion,
        category=category,
        surface_tone=surface_tone,
        face_shape=face_shape,
        body_shape=body_shape,
        height_band=height_band,
        finger_length=finger_length,
        birth_month=birth_month,
        cultural_background=cultural_background,
        personality=personality,
        budget_band=budget_band,
    )
    if not any(picks.values()):
        return "(no matches available — offer to connect the client with our private concierge)"

    layers = [
        ("PRIMARY (perfect match)", picks.get("primary")),
        ("SECONDARY (slight variation)", picks.get("secondary")),
        ("STATEMENT (bolder evolution)", picks.get("statement")),
    ]
    lines = []
    for label, p in layers:
        if not p:
            continue
        stones = p.get("stones") or []
        stones_str = ", ".join(stones) if isinstance(stones, list) else str(stones)
        bits = [
            f"{label}: {p['name']} ({p.get('category','')}, {p.get('metal','')}, {p.get('style','')})",
        ]
        if p.get("cut"):
            bits.append(f"cut: {p['cut']}")
        if stones_str:
            bits.append(f"stones: {stones_str}")
        if p.get("description"):
            bits.append(p["description"])
        if p.get("narrative"):
            bits.append(f"Narrative: {p['narrative']}")
        reasons = p.get("reasons") or []
        if reasons:
            bits.append(f"Reasons: {'; '.join(reasons)}")
        if p.get("url"):
            bits.append(f"Link: {p['url']}")
        lines.append(" | ".join(bits))
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


@function_tool
async def submit_noor_request(
    full_name: str,
    purpose: str,
    timeline: str,
    delivery_location: str,
    contact_method: str,
    contact_detail: str,
) -> str:
    """Submit a Noor Collection allocation request on behalf of the client.

    Call this ONLY after you have collected ALL five fields from the client in
    conversation. The backend stores the request and generates a reference ID.
    The concierge team will review and reach out within 48 hours.

    Args:
        full_name: Client's full name as it should appear on records.
        purpose: The occasion or reason (what this piece means to them).
        timeline: When they'd hope to receive it (e.g. "within 3 months").
        delivery_location: City / country for delivery.
        contact_method: "email", "phone", or "both".
        contact_detail: The actual email address, phone number, or both.

    Returns a confirmation with reference ID, or an error/block reason.
    """
    factory = get_session_factory()
    if factory is None:
        return "(Noor submission unavailable — database not configured. Ask the client to contact service@aueshah.com directly.)"

    from app.core.agents_context import get_current_user_id

    user_id = get_current_user_id()
    if user_id is None:
        return "(Noor submissions require authentication. Please ask the client to log in first.)"

    try:
        async with factory() as session:
            approved_count = await noor_repo.count_approved(session)
            if approved_count >= settings.noor_max_allocations:
                return (
                    "The Noor Collection has reached its full allocation of "
                    f"{settings.noor_max_allocations} pieces. "
                    "This collection is now permanently closed to new requests. "
                    "I'd be happy to guide you toward our other exceptional collections."
                )

            blocking = await noor_repo.user_has_active(session, user_id)
            if blocking is not None:
                if blocking.status == "pending":
                    NOOR_REQUESTS_TOTAL.labels(outcome="blocked_pending").inc()
                    return (
                        f"You already have a pending Noor allocation request "
                        f"(Ref: {blocking.reference_id}). Our concierge team is reviewing it "
                        f"and will reach out personally. In the meantime, I'd love to show you "
                        f"our other collections."
                    )
                if blocking.status == "declined":
                    NOOR_REQUESTS_TOTAL.labels(outcome="blocked_cooldown").inc()
                    return (
                        "The Noor Collection remains exceptionally limited. "
                        "Your prior request has already been reviewed and a decision has been shared. "
                        "I'd be happy to explore our other extraordinary collections with you."
                    )
                NOOR_REQUESTS_TOTAL.labels(outcome="blocked_cooldown").inc()
                return (
                    f"Your previous Noor allocation (Ref: {blocking.reference_id}) is still "
                    f"within the allocation window. I'd love to show you our other collections "
                    f"in the meantime."
                )

            row = await noor_repo.create(
                session,
                user_id=user_id,
                full_name=full_name,
                purpose=purpose,
                timeline=timeline,
                delivery_location=delivery_location,
                contact_method=contact_method,
                contact_details=contact_detail,
            )

        NOOR_REQUESTS_TOTAL.labels(outcome="created").inc()
        return (
            f"Noor allocation request submitted successfully. "
            f"Reference ID: {row.reference_id}. "
            f"Our concierge team will review your request and reach out personally within 48 hours."
        )

    except Exception as e:
        logger.error(f"submit_noor_request tool error: {e}", exc_info=True)
        return "(An error occurred while submitting the request. Please ask the client to contact service@aueshah.com directly.)"


@function_tool
async def submit_appointment(
    email: str,
    appointment_type: str,
    phone: str | None = None,
    preferred_date: str | None = None,
    notes: str | None = None,
) -> str:
    """Submit an appointment request to the Aueshah concierge team.

    Call this ONLY after you have collected the client's email and the type of
    appointment they want (virtual, in-person, bespoke consultation, or
    general). Phone, preferred date, and notes are optional — pass them only if
    the client mentioned them. The backend persists the request and emails the
    concierge team. Use the returned reference ID in your reply to the client.

    Args:
        email: Client email address (required).
        appointment_type: "virtual", "in-person", "bespoke", or "general".
        phone: Optional phone number, if the client offered one.
        preferred_date: Optional free-form preferred time
            (e.g. "next Tuesday afternoon", "between 22 and 24 May").
        notes: Optional extra context the client shared
            (occasion, piece of interest, party size, etc.).

    Returns a confirmation with reference ID, or an error message.
    """
    if "@" not in email or "." not in email:
        return "(That email looks malformed — ask the client to repeat it before submitting.)"

    factory = get_session_factory()
    if factory is None:
        return "(Appointment submission unavailable — database not configured. Ask the client to email service@aueshah.com directly.)"

    from app.core.agents_context import get_current_user_id

    user_id = get_current_user_id()

    try:
        async with factory() as session:
            row = await create_appointment(
                session,
                email=email.strip().lower(),
                appointment_type=appointment_type,
                user_id=user_id,
                phone=phone,
                preferred_date=preferred_date,
                notes=notes,
            )

        APPOINTMENT_REQUESTS_TOTAL.labels(appointment_type=appointment_type).inc()
        return (
            f"Appointment request submitted. Reference: {row.reference_id}. "
            f"Our concierge team will reach out within 24 hours to confirm."
        )

    except Exception as e:
        logger.error(f"submit_appointment tool error: {e}", exc_info=True)
        return "(An error occurred while submitting the appointment. Please ask the client to email service@aueshah.com directly.)"


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
        handoff_description="Consult and recommend Aueshah pieces from our collections (rings, bracelets, earrings, pendants, necklaces, tiaras, waist adornments). Default surface — handles category interest, style questions, 'what suits me'.",
        instructions=_specialist_instructions("product"),
        model=model,
        model_settings=model_settings,
        tools=[recommend_pieces, search_catalog, submit_appointment],
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
        tools=[noor_recommend, submit_noor_request],
    )

    bespoke_agent = Agent(
        name="bespoke",
        handoff_description="Handle custom, made-to-order, one-of-a-kind design requests. Route warmly to our atelier.",
        instructions=_specialist_instructions("bespoke"),
        model=model,
        model_settings=model_settings,
        tools=[submit_appointment],
    )

    general_agent = Agent(
        name="general",
        handoff_description="Handle brand heritage, philosophy, ethical sourcing, appointments, repairs, warranty, sizing, care, and any other non-piece questions. This is the default fallback.",
        instructions=_specialist_instructions("general"),
        model=model,
        model_settings=model_settings,
        tools=[submit_appointment],
    )

    triage_agent = Agent(
        name="triage",
        instructions=(
            "You are the silent routing layer of the Aueshah Concierge.\n"
            "Your ONLY job is to read the client's latest message and hand off "
            "to the most appropriate specialist. You do not write replies yourself.\n\n"
            "HANDOFF RULES (apply in order — first match wins):\n"
            "1. If the message mentions the Noor Collection by name → hand off to `noor`.\n"
            "2. If the message is about custom / bespoke / made-to-order / one-of-a-kind design → hand off to `bespoke`.\n"
            "3. If the message compares two or more specific pieces → hand off to `compare`.\n"
            "4. If the message expresses ANY of the following, hand off to `product`:\n"
            "   - interest in a piece or collection ('I want', 'I'm looking for', 'show me', 'do you have')\n"
            "   - mention of a category (ring, bracelet, earrings, pendant, necklace, tiara, waist adornment, jewelry, jewellery, piece)\n"
            "   - a style or aesthetic question (minimalist, statement, heritage, modern, what suits me)\n"
            "   - request for advice or recommendation ('what do you recommend', 'something for [occasion]', 'help me choose')\n"
            "   - any STATED OCCASION even without a category — engagement, anniversary, gift for [partner/wife/mother/sister/friend], for myself, formal event / wedding / gala, milestone birthday, heirloom / heritage piece. The product skill runs the matching occasion playbook.\n"
            "   - profile information offered without context (age, skin tone, style answer, finger length, personality, birth month)\n"
            "5. Otherwise (pure greetings with no other intent, heritage / brand / philosophy questions, "
            "policies, care, warranty, repair, sizing, explicit appointment requests, anything unclear) → hand off to `general`.\n\n"
            "When in doubt between `product` and `general`, prefer `product` — the client experience "
            "is consultative, not transactional. Never reply directly — always hand off."
        ),
        model=model,
        model_settings=ModelSettings(temperature=0.0),
        handoffs=[noor_agent, bespoke_agent, compare_agent, product_agent, general_agent],
        input_guardrails=[injection_guardrail, off_topic_guardrail],
    )

    return triage_agent
