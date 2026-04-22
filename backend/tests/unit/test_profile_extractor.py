"""Unit tests for the heuristic profile field extractor (T169)."""
from app.services.profile_extractor import diff_against_user, extract_profile_fields


def test_extracts_age_range_from_decade_phrase():
    assert extract_profile_fields("hi, I'm in my 30s")["age_range"] == "30s"
    assert extract_profile_fields("I am in my 50s now")["age_range"] == "50s"


def test_extracts_age_from_numeric_age():
    assert extract_profile_fields("I'm 34 years old")["age_range"] == "30s"
    assert extract_profile_fields("im 27 yo")["age_range"] == "20s"


def test_extracts_skin_tone():
    assert extract_profile_fields("My skin tone is cool")["skin_tone"] == "cool"
    assert extract_profile_fields("I have warm undertones")["skin_tone"] == "warm"
    assert extract_profile_fields("skin tone is neutral")["skin_tone"] == "neutral"


def test_extracts_style_preference():
    assert extract_profile_fields("I prefer minimalist pieces")["style_preference"] == "minimalist"
    assert extract_profile_fields("my style is heritage")["style_preference"] == "heritage"


def test_returns_empty_when_nothing_matches():
    assert extract_profile_fields("Tell me about your collections") == {}


def test_diff_drops_unchanged_values():
    extracted = {"age_range": "30s", "skin_tone": "cool"}
    delta = diff_against_user(
        extracted,  # type: ignore[arg-type]
        current_age_range="30s",
        current_skin_tone=None,
        current_style_preference=None,
    )
    assert delta == {"skin_tone": "cool"}


def test_diff_drops_all_when_unchanged():
    extracted = {"style_preference": "minimalist"}
    delta = diff_against_user(
        extracted,  # type: ignore[arg-type]
        current_age_range=None,
        current_skin_tone=None,
        current_style_preference="minimalist",
    )
    assert delta == {}
