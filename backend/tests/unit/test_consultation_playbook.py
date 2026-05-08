"""Verify the v3.0 consultation playbook is wired into prompts and triage.

These tests don't call the LLM — they assert the playbook trigger phrases
and key axes are physically present in the prompt strings, so the live model
sees them every turn.
"""
from __future__ import annotations

from app.config.prompts import SKILL_PROMPTS, SYSTEM_PROMPT
from app.services.styling_engine import occasion_playbook


def test_system_prompt_lists_sixteen_axes():
    """The operating-intelligence block should enumerate all 16 styling axes."""
    sp = SYSTEM_PROMPT.lower()
    expected_axis_phrases = [
        "age tier",
        "undertone",
        "surface tone",
        "style",
        "face shape",
        "body shape",
        "height",
        "finger length",
        "birth month",
        "cultural background",
        "personality",
        "emotional intent",
        "gem cut",
        "necklace length",
        "visual psychology",
        "wealth signal",
    ]
    for phrase in expected_axis_phrases:
        assert phrase in sp, f"system prompt missing axis: {phrase!r}"


def test_system_prompt_lists_visual_psychology_categories():
    sp = SYSTEM_PROMPT.lower()
    for category in ["high-contrast", "harmony", "royal", "quiet"]:
        assert category in sp, f"system prompt missing psychology category: {category!r}"


def test_system_prompt_mentions_universal_safe_combinations():
    assert "universal safe" in SYSTEM_PROMPT.lower()


def test_system_prompt_describes_reasons_line_handling():
    """The bot must know to echo at most ONE reason per pick, never invent."""
    sp = SYSTEM_PROMPT.lower()
    assert "reasons" in sp
    assert "never invent" in sp


def test_product_skill_has_engagement_playbook():
    p = SKILL_PROMPTS["product"].lower()
    # Trigger phrases the bot listens for.
    assert "engagement" in p
    assert "propose" in p or "she said yes" in p
    # Key axes for this playbook.
    assert "finger_length" in p or "long fingers" in p


def test_product_skill_has_anniversary_playbook():
    p = SKILL_PROMPTS["product"].lower()
    assert "anniversary" in p
    assert "milestone year" in p


def test_product_skill_has_gift_for_mother_playbook():
    p = SKILL_PROMPTS["product"].lower()
    assert "mother" in p or "mom" in p
    assert "birthstone" in p


def test_product_skill_has_self_purchase_playbook():
    p = SKILL_PROMPTS["product"].lower()
    assert "for myself" in p or "self-purchase" in p


def test_product_skill_has_formal_event_playbook():
    p = SKILL_PROMPTS["product"].lower()
    assert "formal event" in p or "wedding" in p or "gala" in p
    assert "ballroom" in p or "venue" in p


def test_product_skill_has_heritage_playbook():
    p = SKILL_PROMPTS["product"].lower()
    assert "heirloom" in p or "heritage" in p


def test_product_skill_warns_against_inventing_reasons():
    p = SKILL_PROMPTS["product"].lower()
    assert "never invent" in p


def test_product_skill_keeps_consultation_default():
    p = SKILL_PROMPTS["product"].lower()
    # Bot must NOT pivot to email/booking proactively.
    assert "submit_appointment" in p
    assert "clearly asked to be scheduled" in p or "clearly asked" in p


def test_general_skill_redirects_occasions_to_product():
    g = SKILL_PROMPTS["general"].lower()
    # General skill should explicitly tell itself NOT to handle stated occasions.
    assert "engagement" in g
    assert "anniversary" in g
    # And explicitly mention handing off to product.
    assert "product skill" in g or "occasion playbook" in g


def test_engagement_playbook_data_consistent_with_prompt():
    """Cross-check: the JSON-encoded playbook keys should match the prompt's
    trigger phrases. If we add an occasion to the JSON, we must add it to the
    prompt too."""
    pb = occasion_playbook("engagement")
    assert pb is not None
    assert pb["category"] == "ring"
    assert "finger_length" in pb["key_dimensions"]
    # Prompt must mention rings + finger_length so the LLM actually uses them.
    p = SKILL_PROMPTS["product"].lower()
    assert "ring" in p
    assert "finger" in p


def test_anniversary_playbook_data_consistent_with_prompt():
    pb = occasion_playbook("anniversary")
    assert pb is not None
    assert pb["depth"] == "three_tier"
    p = SKILL_PROMPTS["product"].lower()
    assert "three tier" in p.replace("-", " ").replace("3", "three") or "3-tier" in p


def test_all_documented_playbooks_have_json_entries():
    """If the prompt references an occasion playbook, the JSON must encode it.
    Mismatches would cause the matcher to silently drop signals."""
    documented = [
        "engagement",
        "anniversary",
        "gift_for_partner",
        "gift_for_mother",
        "gift_for_friend",
        "self_purchase",
        "formal_event",
        "milestone_birthday",
        "heritage_addition",
    ]
    for o in documented:
        assert occasion_playbook(o) is not None, f"missing JSON playbook entry: {o}"


# ─────────────────────────────────────────────────────────────────────────
# Regression coverage for the engagement-mis-routed-to-bespoke bug
# (live test on 2026-05-09 produced: "we can explore a custom design …
# may I have your email? Our team will use it to coordinate your bespoke
# consultation"). Two roots: triage rule 2 too loose, bespoke prompt
# email-first. These tests pin both fixes in place.
# ─────────────────────────────────────────────────────────────────────────

def test_bespoke_skill_is_consult_first_not_email_first():
    """Bespoke must consult deeply before any email/appointment pivot."""
    b = SKILL_PROMPTS["bespoke"].lower()
    # Must explicitly forbid email on first turn.
    assert "consult first" in b or "deep consultation" in b
    assert "first turn" in b
    # Must list consultation topics, not jump to logistics.
    assert "occasion" in b
    assert "style direction" in b or "style" in b
    assert "stone" in b


def test_bespoke_skill_blocks_first_turn_email_phrases():
    """The exact phrases the bot used in the live bug must be flagged as forbidden."""
    b = SKILL_PROMPTS["bespoke"]
    # Any sentence whose lowercase form contains all these phrases together
    # is the bug pattern. Confirm the prompt explicitly forbids them.
    assert "may I have your email" in b
    assert "as we shape your ring together" in b
    assert "let's get you scheduled" in b.lower() or "our team will use it" in b.lower()


def test_bespoke_skill_gates_appointment_on_explicit_request():
    """submit_appointment must only fire on explicit booking phrases."""
    b = SKILL_PROMPTS["bespoke"].lower()
    assert "submit_appointment" in b
    # At least one explicit-request trigger phrase listed.
    assert "book me" in b or "i'd like to come in" in b or "have someone reach out" in b


def test_bespoke_skill_can_surface_catalog_pieces():
    """The agent gets recommend_pieces — the prompt must tell it when to use it."""
    b = SKILL_PROMPTS["bespoke"].lower()
    assert "recommend_pieces" in b
    # Frame as courtesy, not redirect.
    assert "courtesy" in b or "before we go fully bespoke" in b


def test_triage_has_explicit_engagement_to_product_anti_pattern():
    """Triage rule 2 must list engagement / anniversary / wedding / gift as
    NEVER-route-to-bespoke unless an explicit custom-design phrase is also present."""
    from app.core.agents_factory import build_triage_agent

    build_triage_agent.cache_clear()  # force rebuild after prompt edits
    agent = build_triage_agent()
    instr = agent.instructions.lower()

    # Anti-pattern label and at least the engagement / anniversary / gift cues.
    assert "anti-pattern" in instr
    assert "engagement" in instr
    assert "anniversary" in instr
    assert "wedding" in instr
    assert "gift for" in instr or "gift for my" in instr

    # The route for those is product, not bespoke.
    assert "always go to `product`" in instr or "always go to product" in instr


def test_triage_requires_explicit_custom_phrase_for_bespoke():
    """Triage must enumerate explicit custom-design phrases that DO route to bespoke."""
    from app.core.agents_factory import build_triage_agent

    build_triage_agent.cache_clear()
    agent = build_triage_agent()
    instr = agent.instructions.lower()

    for phrase in [
        "bespoke",
        "custom-made",
        "made-to-order",
        "one-of-a-kind",
        "design from scratch",
    ]:
        assert phrase in instr, f"triage missing explicit bespoke trigger: {phrase!r}"


def test_triage_default_tie_break_favours_product_over_bespoke():
    """When in doubt between bespoke and product, prefer product."""
    from app.core.agents_factory import build_triage_agent

    build_triage_agent.cache_clear()
    agent = build_triage_agent()
    instr = agent.instructions.lower()
    assert "doubt between `bespoke` and `product`" in instr or "doubt between bespoke and product" in instr
    assert "prefer `product`" in instr or "prefer product" in instr


# ─────────────────────────────────────────────────────────────────────────
# UNIVERSAL CONSULT-FIRST RULE — applies to every skill, every chat,
# not just engagement / not just bespoke. The client's directive: bot must
# behave as a level-5 luxury consultant in EVERY conversation, never pivot
# to "team will reach out / give us your email" on the first turn.
# ─────────────────────────────────────────────────────────────────────────

def test_system_prompt_has_universal_consult_first_rule():
    sp = SYSTEM_PROMPT
    assert "UNIVERSAL CONSULT-FIRST RULE" in sp
    assert "LEVEL-5 LUXURY CONSULTANT" in sp
    # Must enumerate explicit booking triggers AND consultation cues distinctly.
    assert "EXPLICIT BOOKING TRIGGER PHRASES" in sp
    assert "CONSULTATION CUES" in sp
    assert "FIRST-TURN FORBIDDEN PHRASES" in sp


def test_system_prompt_forbids_the_live_bug_phrases():
    """The exact phrases the bot used in the live engagement-ring bug must be
    explicitly listed as forbidden."""
    sp = SYSTEM_PROMPT.lower()
    for phrase in [
        "may i have your email",
        "let's get you scheduled",
        "our team will use it to coordinate",
        "as we shape your",  # covers "as we shape your ring together"
        "i'll have someone follow up",
    ]:
        assert phrase in sp, f"system prompt missing forbidden-phrase listing: {phrase!r}"


def test_system_prompt_lists_consultation_cues_that_must_not_collect_email():
    sp = SYSTEM_PROMPT.lower()
    # All occasion / category / style cues must be explicitly listed as NEVER booking triggers.
    for cue in [
        "engagement",
        "anniversary",
        "wedding",
        "gift for",
        "milestone birthday",
        "heirloom",
        "tell me about your collection",
        "what suits me",
    ]:
        assert cue in sp, f"system prompt missing consultation cue: {cue!r}"


def test_non_negotiable_rule_7_gates_appointment_on_explicit_ask():
    """Rule 7 must only authorise email collection AFTER an explicit booking trigger."""
    sp = SYSTEM_PROMPT
    assert "EXPLICIT BOOKING TRIGGER PHRASE" in sp
    # The "do not" half must explicitly call out occasion / category / style cues.
    assert "consultation" in sp.lower()
    assert "let the client surface" in sp.lower() or "consult first" in sp.lower()


def test_general_skill_lists_universal_forbidden_phrases():
    """The general skill is the most likely path for premature email collection.
    It must mirror the universal forbidden-phrase list."""
    g = SKILL_PROMPTS["general"].lower()
    for phrase in [
        "may i have your email",
        "let's get you scheduled",
        "our team will use it to coordinate",
    ]:
        assert phrase in g, f"general skill missing forbidden-phrase listing: {phrase!r}"


def test_general_skill_redirects_all_consultation_cues_not_just_engagement():
    """The 'do NOT trigger appointment on these' list must cover the full set of
    consultation cues, not just engagement."""
    g = SKILL_PROMPTS["general"].lower()
    for cue in [
        "engagement",
        "anniversary",
        "wedding",
        "gift for",
        "formal event",
        "milestone birthday",
        "heirloom",
        "what suits me",
    ]:
        assert cue in g, f"general skill missing consultation-cue redirect: {cue!r}"


def test_no_skill_prompt_has_first_turn_email_collection_as_default():
    """SAFETY NET — no skill should authorise email collection as a default
    behaviour. Any reference to email/scheduling must be conditional on an
    explicit client request."""
    for skill_key in ("product", "bespoke", "general"):
        body = SKILL_PROMPTS[skill_key].lower()
        if "submit_appointment" not in body:
            continue  # skill doesn't collect contact info at all
        # If the skill talks about appointments, it MUST gate the flow on an
        # explicit ask. We accept any of these gating phrases.
        gating_phrases = [
            "only when the client",
            "only on explicit",
            "only after",
            "strictly gated",
            "clearly asked",
            "explicit booking",
            "explicit request",
            "explicitly asked",
        ]
        assert any(p in body for p in gating_phrases), (
            f"skill {skill_key!r} discusses appointments but does not gate the flow "
            f"on an explicit client ask"
        )


def test_operating_intelligence_block_forbids_premature_email_collection():
    sp = SYSTEM_PROMPT.lower()
    # Forbidden behaviors block must call out email/contact prematurity.
    assert "forbidden behaviors" in sp
    assert "email" in sp
    assert "before the client has" in sp or "explicit booking trigger" in sp
