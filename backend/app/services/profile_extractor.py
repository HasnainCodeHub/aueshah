"""T169b: Heuristic profile-field extraction from user messages.

This is a deliberately conservative regex extractor — we only emit a field
when the client phrasing is unambiguous. Anything fuzzier is left for the
specialist agents to ask about explicitly.

The extractor never overwrites an existing field; the caller is responsible
for skipping fields the user has already set.
"""
from __future__ import annotations

import re
from typing import Optional, TypedDict

_AGE_RANGE_RE = re.compile(r"\b(?:i'?m|i am|im)\s+in\s+my\s+(20|30|40|50|60|70)s\b", re.I)
_AGE_NUMERIC_RE = re.compile(r"\b(?:i'?m|i am|im)\s+(\d{2})\s*(?:years?\s*old|y[/.]?o)?\b", re.I)

_SKIN_TONE_RE = re.compile(r"\b(?:my\s+)?skin\s+tone\s+is\s+(cool|warm|neutral)\b", re.I)
_SKIN_TONE_ALT_RE = re.compile(r"\bi\s+have\s+(cool|warm|neutral)\s+(?:skin|undertones?)\b", re.I)

_STYLE_RE = re.compile(
    r"\b(?:i\s+(?:prefer|like|love)|my\s+style\s+is)\s+(minimalist|statement|heritage|modern)\b",
    re.I,
)


class ExtractedProfile(TypedDict, total=False):
    age_range: str
    skin_tone: str
    style_preference: str


def _age_to_range(age: int) -> Optional[str]:
    if age < 18 or age > 99:
        return None
    decade = (age // 10) * 10
    return f"{decade}s"


def extract_profile_fields(message: str) -> ExtractedProfile:
    """Pull any unambiguous profile fields from a single user message."""
    if not message:
        return {}

    out: ExtractedProfile = {}

    if (m := _AGE_RANGE_RE.search(message)):
        out["age_range"] = f"{m.group(1)}s"
    elif (m := _AGE_NUMERIC_RE.search(message)):
        rng = _age_to_range(int(m.group(1)))
        if rng:
            out["age_range"] = rng

    if (m := _SKIN_TONE_RE.search(message)) or (m := _SKIN_TONE_ALT_RE.search(message)):
        out["skin_tone"] = m.group(1).lower()

    if (m := _STYLE_RE.search(message)):
        out["style_preference"] = m.group(1).lower()

    return out


def diff_against_user(
    extracted: ExtractedProfile,
    *,
    current_age_range: Optional[str],
    current_skin_tone: Optional[str],
    current_style_preference: Optional[str],
) -> ExtractedProfile:
    """Drop any extracted field whose value already matches what the user has."""
    out: ExtractedProfile = {}
    if "age_range" in extracted and extracted["age_range"] != current_age_range:
        out["age_range"] = extracted["age_range"]
    if "skin_tone" in extracted and extracted["skin_tone"] != current_skin_tone:
        out["skin_tone"] = extracted["skin_tone"]
    if "style_preference" in extracted and extracted["style_preference"] != current_style_preference:
        out["style_preference"] = extracted["style_preference"]
    return out
