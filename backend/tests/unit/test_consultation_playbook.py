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
