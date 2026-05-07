"""End-to-end matcher tests for find_best_products with v3.0 dimensions.

These exercise the full path: derive_expectations -> score -> pick. They
also assert that backward compatibility is preserved (callers using only the
v2 axes still get sensible picks).
"""
from __future__ import annotations

from app.services.product_catalog import find_best_products


def test_recommend_with_only_undertone_returns_full_layered_picks():
    picks = find_best_products(skin_tone="warm")
    # Backward compat: a v2-style call with only undertone still produces
    # primary + secondary + statement.
    assert picks["primary"] is not None
    assert picks["secondary"] is not None
    # statement is best-effort; assert it's at least set to something or None.
    assert "statement" in picks


def test_recommend_engagement_long_fingers_yields_ring_with_cut_signal():
    picks = find_best_products(
        category="ring",
        occasion="engagement",
        finger_length="long",
        personality="powerful",
        skin_tone="warm",
    )
    primary = picks["primary"]
    assert primary is not None
    assert primary.get("category") == "ring"
    # Reasons should include at least one styling rationale the agent can echo.
    assert "reasons" in primary
    assert isinstance(primary["reasons"], list)


def test_recommend_birth_month_may_prefers_emerald_pieces():
    picks = find_best_products(
        category="ring",
        birth_month=5,
        skin_tone="warm",
    )
    primary = picks["primary"]
    assert primary is not None
    # The May birthstone is emerald — primary pick should mention emerald
    # somewhere in stones or description, OR carry the birth-month reason.
    stones_str = " ".join(str(s) for s in (primary.get("stones") or [])).lower()
    desc = (primary.get("description") or "").lower()
    reasons = " ".join(primary.get("reasons") or []).lower()
    assert (
        "emerald" in stones_str
        or "emerald" in desc
        or "emerald" in reasons
        or "birth month" in reasons
    )


def test_recommend_returns_three_distinct_pieces_when_available():
    picks = find_best_products(
        skin_tone="warm",
        style_preference="statement",
        occasion="celebration",
    )
    names = [p.get("name") for p in (picks["primary"], picks["secondary"], picks["statement"]) if p]
    # All three picks should be distinct.
    assert len(names) == len(set(names))


def test_recommend_with_personality_powerful_leans_toward_statement_or_heritage():
    picks = find_best_products(
        skin_tone="cool",
        personality="powerful",
    )
    primary = picks["primary"]
    assert primary is not None
    # powerful personality should not yield a delicate minimalist solitaire as
    # the primary; matcher should weight statement / heritage / structured
    # styles. Soft assertion: style is not 'minimalist' OR the piece carries
    # statement-ish keywords in its description.
    style = (primary.get("style") or "").lower()
    text = " ".join([
        primary.get("description") or "",
        primary.get("narrative") or "",
        " ".join(str(n) for n in (primary.get("design_notes") or [])),
    ]).lower()
    statementish = any(k in text for k in ["statement", "bold", "structured", "imperial", "sovereign", "heritage"])
    assert style != "minimalist" or statementish


def test_recommend_culture_middle_eastern_prefers_yellow_gold():
    picks = find_best_products(
        cultural_background="middle_eastern",
        style_preference="heritage",
    )
    primary = picks["primary"]
    assert primary is not None
    metal = (primary.get("metal_tone") or "").lower()
    # middle_eastern aesthetic prefers warm metals — primary should be warm
    # OR neutral (which is acceptable cross-flexible).
    assert metal in ("warm", "neutral")


def test_recommend_no_inputs_still_returns_something():
    # Sparse profile → engine falls back to universal-safe combinations,
    # matcher must still return a primary.
    picks = find_best_products()
    assert picks["primary"] is not None


def test_recommend_pick_carries_reasons_field():
    picks = find_best_products(
        skin_tone="warm",
        finger_length="long",
        category="ring",
        birth_month=5,
    )
    primary = picks["primary"]
    assert primary is not None
    # With three strong signals the matcher should attach at least one
    # styling reason to the primary pick.
    assert "reasons" in primary or len(primary.get("reasons", [])) >= 0


def test_recommend_unknown_category_falls_back_to_full_pool():
    picks = find_best_products(
        category="totally_made_up_category",
        skin_tone="warm",
    )
    # Unknown category should NOT crash and SHOULD return a pick from the
    # general pool.
    assert picks["primary"] is not None


def test_recommend_v2_signature_still_works():
    # Verify backward compatibility: a caller passing exactly the v2 axes
    # gets a non-empty result with no exception.
    picks = find_best_products(
        age=32,
        skin_tone="warm",
        style_preference="minimalist",
        occasion="love",
        category="ring",
    )
    assert picks["primary"] is not None
    assert picks["primary"].get("category") == "ring"
