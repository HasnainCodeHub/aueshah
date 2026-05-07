"""Unit tests for app/services/styling_engine.py.

Each test exercises a single styling axis from the v3.0 PDF spec, plus the
graceful-degradation cases (sparse profile, unknown values).
"""
from __future__ import annotations

from app.services.styling_engine import (
    Expectations,
    birthstone_for,
    derive_expectations,
    occasion_playbook,
)


def test_no_inputs_falls_back_to_universal_safe_combinations():
    exp = derive_expectations()
    # With nothing supplied, engine should still seed expectations from the
    # universal-safe combinations so the matcher has something to score on.
    assert any(tone == "cool" for tone, _ in exp.metal_tones)
    assert any(tone == "warm" for tone, _ in exp.metal_tones)
    assert any(stone == "diamond" for stone, _ in exp.gem_categories)
    assert "universal-safe pairing" in exp.reasons


def test_warm_undertone_yields_warm_metals_strongly():
    exp = derive_expectations(undertone="warm")
    # warm undertone should weight warm metals at 4 (best), not soft 1.
    assert exp.weight_for("warm", "metal_tones") == 4
    # white/cool metals are NOT in 'best' for warm, but the schema also
    # doesn't list them as 'avoid' explicitly for warm — yellow_gold / rose_gold
    # are best, so cool should score zero from this axis alone.
    assert exp.weight_for("cool", "metal_tones") == 0
    assert any("warm undertone" in r for r in exp.reasons)


def test_cool_undertone_avoids_warm_metals():
    exp = derive_expectations(undertone="cool")
    assert exp.weight_for("cool", "metal_tones") == 4
    # cool undertone explicitly avoids yellow_gold per the PDF.
    assert "warm" in exp.avoid_metals


def test_neutral_undertone_accepts_all_metals():
    exp = derive_expectations(undertone="neutral")
    assert exp.weight_for("warm", "metal_tones") == 4
    assert exp.weight_for("cool", "metal_tones") == 4


def test_birth_month_may_yields_emerald():
    exp = derive_expectations(birth_month=5)
    assert exp.weight_for("emerald", "gem_categories") == 4
    assert any("birth month 5 → emerald" in r for r in exp.reasons)


def test_birth_month_october_alternate_tourmaline():
    exp = derive_expectations(birth_month=10)
    # Primary is opal (weight 4), alternate is tourmaline (weight 2).
    assert exp.weight_for("opal", "gem_categories") == 4
    assert exp.weight_for("tourmaline", "gem_categories") == 2


def test_face_shape_round_yields_vertical_drop_for_earrings():
    exp = derive_expectations(face_shape="round", category="earrings")
    assert exp.weight_for("long_drop", "style_keywords") == 3
    assert exp.weight_for("vertical", "style_keywords") == 3
    # The PDF tells us round faces should AVOID large round hoops.
    assert "large_circular_hoops" in exp.avoid_keywords


def test_face_shape_oval_for_rings_does_not_pollute_style():
    # Rings have no face-shape rule — face guidance only applies to
    # earrings/necklaces. Engine must respect category gating.
    exp = derive_expectations(face_shape="oval", category="ring")
    # No earring/necklace style guidance should leak into a ring lookup.
    assert exp.weight_for("stud", "style_keywords") == 0
    assert exp.weight_for("choker", "style_keywords") == 0


def test_finger_length_long_yields_emerald_cut_for_rings():
    exp = derive_expectations(finger_length="long", category="ring")
    assert exp.weight_for("emerald", "cuts") == 4
    assert exp.weight_for("princess", "cuts") == 4
    assert any("long fingers" in r for r in exp.reasons)


def test_finger_length_short_avoids_marquise_and_wide_bands():
    exp = derive_expectations(finger_length="short", category="ring")
    assert exp.weight_for("oval", "cuts") == 4
    assert "wide_thick_bands" in exp.avoid_keywords
    assert "marquise" in exp.avoid_keywords


def test_finger_length_long_does_not_pollute_earrings():
    exp = derive_expectations(finger_length="long", category="earrings")
    # finger-to-cut should be gated to rings only.
    assert exp.weight_for("emerald", "cuts") == 0


def test_culture_middle_eastern_yields_yellow_gold_and_emerald_layered():
    exp = derive_expectations(cultural_background="middle_eastern")
    assert exp.weight_for("warm", "metal_tones") == 3
    assert exp.weight_for("emerald", "gem_categories") == 2
    assert exp.weight_for("layered", "style_keywords") == 2
    assert any("middle_eastern aesthetic" in r for r in exp.reasons)


def test_culture_european_yields_quiet_luxury():
    exp = derive_expectations(cultural_background="european")
    assert exp.weight_for("cool", "metal_tones") == 3
    assert exp.weight_for("diamond", "gem_categories") == 2
    assert exp.weight_for("minimalist", "style_keywords") == 2


def test_personality_powerful_yields_emerald_cut_and_platinum():
    exp = derive_expectations(personality="powerful")
    # powerful → platinum (cool) + emerald + statement-style keywords
    assert exp.weight_for("cool", "metal_tones") == 3
    assert exp.weight_for("emerald", "gem_categories") == 2
    assert exp.weight_for("statement", "style_keywords") == 3
    assert exp.weight_for("emerald_cut", "style_keywords") == 3


def test_personality_romantic_yields_rose_gold_morganite():
    exp = derive_expectations(personality="romantic")
    assert exp.weight_for("warm", "metal_tones") == 3
    assert exp.weight_for("morganite", "gem_categories") == 2


def test_body_shape_petite_yields_delicate_avoid_oversized():
    exp = derive_expectations(body_shape="petite")
    assert exp.weight_for("delicate", "scale_keywords") == 3
    assert exp.weight_for("delicate", "style_keywords") == 2
    assert "oversized" in exp.avoid_keywords


def test_body_shape_tall_slim_yields_statement_scale():
    exp = derive_expectations(body_shape="tall_slim")
    assert exp.weight_for("statement", "scale_keywords") == 3
    assert exp.weight_for("statement", "style_keywords") == 2


def test_height_short_avoids_oversized():
    exp = derive_expectations(height_band="short")
    assert exp.weight_for("small", "scale_keywords") == 2
    assert "oversized_earrings" in exp.avoid_keywords


def test_surface_tone_olive_yields_emerald_and_warm_metals():
    exp = derive_expectations(surface_tone="olive")
    assert exp.weight_for("emerald", "gem_categories") == 3
    # Should also fall back to warm metals via surface→undertone crosswalk.
    assert exp.weight_for("warm", "metal_tones") >= 2


def test_surface_tone_only_falls_back_to_undertone_crosswalk():
    # No explicit undertone, only surface tone → engine should still
    # seed metal expectations via the surface→undertone crosswalk.
    exp = derive_expectations(surface_tone="deep")
    assert exp.weight_for("warm", "metal_tones") >= 2


def test_engagement_occasion_psychology_is_harmony():
    exp = derive_expectations(occasion="engagement")
    assert exp.psychology_category == "harmony"


def test_anniversary_occasion_psychology_is_royal():
    exp = derive_expectations(occasion="anniversary")
    assert exp.psychology_category == "royal"


def test_unknown_occasion_yields_no_psychology():
    exp = derive_expectations(occasion="totally_made_up_occasion")
    assert exp.psychology_category is None


def test_engagement_playbook_is_findable():
    pb = occasion_playbook("engagement")
    assert pb is not None
    assert "ring" == pb.get("category")
    assert "finger_length" in pb.get("key_dimensions", [])


def test_birthstone_helper():
    assert birthstone_for(5) == "emerald"
    assert birthstone_for(7) == "ruby"
    assert birthstone_for(13) is None


def test_combined_profile_engagement_powerful_long_fingers():
    # Real-world engagement consultation: powerful personality, long fingers,
    # warm undertone → expect emerald cut + warm metal + statement style.
    exp = derive_expectations(
        occasion="engagement",
        category="ring",
        personality="powerful",
        finger_length="long",
        undertone="warm",
    )
    assert exp.weight_for("emerald", "cuts") == 4
    assert exp.weight_for("warm", "metal_tones") == 4
    assert exp.weight_for("statement", "style_keywords") == 3
    assert exp.psychology_category == "harmony"
    # Reasons should accumulate at least three signals.
    assert len(exp.reasons) >= 3


def test_is_avoided_blocks_metal_in_avoid_list():
    exp = derive_expectations(undertone="cool")
    assert exp.is_avoided("warm", None) is True
    assert exp.is_avoided("cool", None) is False


def test_expectations_is_dataclass_constructible():
    e = Expectations()
    assert e.metal_tones == []
    assert e.psychology_category is None
