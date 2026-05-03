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
_AGE_NUMERIC_RE = re.compile(
    r"\b(?:i'?m|i am|im|my\s+age\s+is|age\s*[:=]?\s*|aged?)\s+(\d{2})\b",
    re.I,
)
_AGE_YEARS_OLD_RE = re.compile(r"\b(\d{2})\s*(?:years?\s*old|y[/.]?o)\b", re.I)

_SKIN_TONE_RE = re.compile(
    r"\b(?:my\s+)?(?:skin\s+tone|undertone|complexion)\s+is\s+(cool|warm|neutral|fair|olive|deep|light|medium|dark)\b",
    re.I,
)
_SKIN_TONE_ALT_RE = re.compile(
    r"\bi\s+have\s+(?:a\s+)?(cool|warm|neutral|fair|olive|deep|light|medium|dark)\s+(?:skin|undertones?|complexion)\b",
    re.I,
)

_STYLE_RE = re.compile(
    r"\b(?:i\s+(?:prefer|like|love|enjoy)|my\s+(?:style|taste|aesthetic)\s+is|(?:i\s+have\s+)?(?:a\s+)?(?:more\s+)?(?:of\s+)?(?:a\s+)?)\s*(minimalist|statement|heritage|modern|classical|classic|traditional|contemporary|vintage|bold)\b",
    re.I,
)

_NAME_RE = re.compile(
    r"\b(?:my\s+name\s+is|i'?m|i am|call\s+me|this\s+is|name\s*[:=]?)\s+([A-Z][a-zA-Z'-]{1,30})(?:\s+([A-Z][a-zA-Z'-]{1,30}))?\b",
)
_NAME_BLOCKLIST = {
    "interested", "looking", "buying", "wondering", "thinking", "ready", "considering",
    "trying", "hoping", "planning", "checking", "browsing", "exploring", "from",
    "back", "here", "online", "new", "happy", "sorry", "good", "fine", "okay",
    "sure", "afraid", "going", "feeling", "actually", "still",
}


class ExtractedProfile(TypedDict, total=False):
    age_range: str
    skin_tone: str
    style_preference: str
    display_name: str


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
    elif (m := _AGE_NUMERIC_RE.search(message)) or (m := _AGE_YEARS_OLD_RE.search(message)):
        rng = _age_to_range(int(m.group(1)))
        if rng:
            out["age_range"] = rng

    if (m := _SKIN_TONE_RE.search(message)) or (m := _SKIN_TONE_ALT_RE.search(message)):
        out["skin_tone"] = m.group(1).lower()

    if (m := _STYLE_RE.search(message)):
        out["style_preference"] = m.group(1).lower()

    if (m := _NAME_RE.search(message)):
        first = m.group(1).strip()
        last = (m.group(2) or "").strip()
        if first.lower() not in _NAME_BLOCKLIST and len(first) >= 2:
            full = (first + (" " + last if last else "")).strip()
            out["display_name"] = full

    return out


def diff_against_user(
    extracted: ExtractedProfile,
    *,
    current_age_range: Optional[str] = None,
    current_skin_tone: Optional[str] = None,
    current_style_preference: Optional[str] = None,
    current_display_name: Optional[str] = None,
) -> ExtractedProfile:
    """Drop any extracted field whose value already matches what the user has."""
    out: ExtractedProfile = {}
    if "age_range" in extracted and extracted["age_range"] != current_age_range:
        out["age_range"] = extracted["age_range"]
    if "skin_tone" in extracted and extracted["skin_tone"] != current_skin_tone:
        out["skin_tone"] = extracted["skin_tone"]
    if "style_preference" in extracted and extracted["style_preference"] != current_style_preference:
        out["style_preference"] = extracted["style_preference"]
    if "display_name" in extracted:
        cur = (current_display_name or "").strip()
        # Don't overwrite a real name with one that's just an email prefix or stub
        if extracted["display_name"] != cur and ("@" in cur or not cur or cur == cur.lower()):
            out["display_name"] = extracted["display_name"]
    return out
