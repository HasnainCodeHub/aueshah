"""Styling engine — derives expected jewelry traits from a client profile.

Reads `data/styling_rules.json` (the v3.0 PDF-encoded rules) and converts any
subset of the 16 styling axes into a graded set of *expectations* a piece can
be scored against. Pure-function, deterministic, no I/O beyond the one-time
JSON load. Missing dimensions degrade silently — no penalty, no signal.

Used by services/product_catalog.py during scoring; can also be called from
tests or future tools.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_RULES_PATH = Path(__file__).resolve().parent.parent / "data" / "styling_rules.json"
_RULES_CACHE: dict[str, Any] | None = None


def _load_rules() -> dict[str, Any]:
    global _RULES_CACHE
    if _RULES_CACHE is not None:
        return _RULES_CACHE
    try:
        with _RULES_PATH.open(encoding="utf-8") as f:
            _RULES_CACHE = json.load(f)
    except Exception as exc:
        logger.error(f"Failed to load styling_rules.json: {exc}")
        _RULES_CACHE = {}
    return _RULES_CACHE


@dataclass
class Expectations:
    """Graded expectations derived from a client profile.

    Each list is weighted by source-rule strength (4 = strong best-match,
    2 = secondary, 1 = soft). Use `weight_for(value, list)` to score a piece.
    """

    metal_tones: list[tuple[str, int]] = field(default_factory=list)
    gem_categories: list[tuple[str, int]] = field(default_factory=list)
    cuts: list[tuple[str, int]] = field(default_factory=list)
    style_keywords: list[tuple[str, int]] = field(default_factory=list)
    scale_keywords: list[tuple[str, int]] = field(default_factory=list)
    avoid_metals: list[str] = field(default_factory=list)
    avoid_keywords: list[str] = field(default_factory=list)
    psychology_category: Optional[str] = None
    reasons: list[str] = field(default_factory=list)

    def weight_for(self, value: Optional[str], dimension: str) -> int:
        """Return the strongest weight for `value` in the named dimension list."""
        if not value:
            return 0
        v = value.lower().replace(" ", "_")
        bag = {
            "metal_tones": self.metal_tones,
            "gem_categories": self.gem_categories,
            "cuts": self.cuts,
            "style_keywords": self.style_keywords,
            "scale_keywords": self.scale_keywords,
        }.get(dimension, [])
        best = 0
        for k, w in bag:
            if k.lower() == v and w > best:
                best = w
        return best

    def is_avoided(self, metal_tone: Optional[str], style: Optional[str]) -> bool:
        if metal_tone and metal_tone.lower() in self.avoid_metals:
            return True
        if style and style.lower() in self.avoid_keywords:
            return True
        return False


# ---------- per-axis derivation helpers ----------


def _add(bag: list[tuple[str, int]], key: str, weight: int) -> None:
    if not key:
        return
    bag.append((key.lower(), weight))


# Crosswalk: surface_tone -> compact undertone family used by metal scorer.
# Keeps the engine usable when only surface_tone (fair/medium/deep) is given.
_SURFACE_TO_UNDERTONE = {
    "fair": "cool",
    "light": "cool",
    "medium": "warm",
    "olive": "warm",
    "tan": "warm",
    "deep": "warm",
}

# Map descriptive metal names from the rules JSON onto the catalog's
# `metal_tone` taxonomy (cool/warm/neutral). Catalog uses three buckets;
# the rules use specific metals. This crosswalk lets the matcher score.
_METAL_NAME_TO_TONE = {
    "white_gold": "cool",
    "platinum": "cool",
    "silver": "cool",
    "rhodium": "cool",
    "yellow_gold": "warm",
    "rose_gold": "warm",
    "champagne_gold": "warm",
    "copper": "warm",
}


def _expand_metals(metal_names: list[str], weight: int) -> list[tuple[str, int]]:
    """Convert specific metal names into catalog tone buckets with weight."""
    out: list[tuple[str, int]] = []
    for m in metal_names:
        tone = _METAL_NAME_TO_TONE.get(m.lower())
        if tone:
            out.append((tone, weight))
    return out


def _from_undertone(rules: dict, undertone: Optional[str], exp: Expectations) -> None:
    if not undertone:
        return
    block = rules.get("undertone_to_metal", {}).get(undertone.lower())
    if not block:
        return
    exp.metal_tones.extend(_expand_metals(block.get("best", []), 4))
    exp.metal_tones.extend(_expand_metals(block.get("secondary", []), 2))
    for m in block.get("avoid", []):
        tone = _METAL_NAME_TO_TONE.get(m.lower())
        if tone:
            exp.avoid_metals.append(tone)
    if block.get("best"):
        exp.reasons.append(f"{undertone} undertone → {block['best'][0].replace('_', ' ')}")


def _from_surface_tone(rules: dict, surface_tone: Optional[str], exp: Expectations) -> None:
    if not surface_tone:
        return
    block = rules.get("surface_tone_to_gem", {}).get(surface_tone.lower())
    if not block:
        return
    for stone in block.get("best", []):
        _add(exp.gem_categories, stone, 3)
    exp.metal_tones.extend(_expand_metals(block.get("metals", []), 2))
    if block.get("best"):
        exp.reasons.append(f"{surface_tone} skin → {block['best'][0]}")


def _from_face_shape(
    rules: dict, face_shape: Optional[str], category: Optional[str], exp: Expectations
) -> None:
    if not face_shape:
        return
    block = rules.get("face_shape_to_form", {}).get(face_shape.lower())
    if not block:
        return
    if category in (None, "earrings"):
        for form in block.get("earrings", []):
            _add(exp.style_keywords, form, 3)
    if category in (None, "necklace"):
        for form in block.get("necklaces", []):
            _add(exp.style_keywords, form, 3)
    for av in block.get("avoid", []):
        exp.avoid_keywords.append(av.lower())
    if block.get("earrings") or block.get("necklaces"):
        exp.reasons.append(f"{face_shape} face → {block.get('goal', 'balanced silhouette')}")


def _from_body_shape(rules: dict, body_shape: Optional[str], exp: Expectations) -> None:
    if not body_shape:
        return
    block = rules.get("body_to_scale", {}).get(body_shape.lower())
    if not block:
        return
    for s in block.get("scale", []):
        _add(exp.scale_keywords, s, 3)
    for k in block.get("keywords", []):
        _add(exp.style_keywords, k, 2)
    for av in block.get("avoid", []):
        exp.avoid_keywords.append(av.lower())
    if block.get("scale"):
        exp.reasons.append(f"{body_shape} body → {block['scale'][0]} scale")


def _from_height(rules: dict, height_band: Optional[str], exp: Expectations) -> None:
    if not height_band:
        return
    block = rules.get("height_to_size", {}).get(height_band.lower())
    if not block:
        return
    for s in block.get("scale", []):
        _add(exp.scale_keywords, s, 2)
    for av in block.get("avoid", []):
        exp.avoid_keywords.append(av.lower())


def _from_finger_length(
    rules: dict, finger_length: Optional[str], category: Optional[str], exp: Expectations
) -> None:
    if not finger_length:
        return
    block = rules.get("finger_to_cut", {}).get(finger_length.lower())
    if not block:
        return
    if category in (None, "ring"):
        for c in block.get("cuts", []):
            _add(exp.cuts, c, 4)
    for av in block.get("avoid", []):
        exp.avoid_keywords.append(av.lower())
    if block.get("cuts"):
        exp.reasons.append(f"{finger_length} fingers → {block['cuts'][0].replace('_', ' ')} cut")


def _from_birth_month(rules: dict, birth_month: Optional[int], exp: Expectations) -> None:
    if not birth_month:
        return
    key = str(int(birth_month))
    block = rules.get("birth_month_to_stone", {}).get(key)
    if not block:
        return
    primary = block.get("primary")
    if primary:
        _add(exp.gem_categories, primary, 4)
        exp.reasons.append(f"birth month {key} → {primary}")
    if block.get("alternate"):
        _add(exp.gem_categories, block["alternate"], 2)


def _from_culture(rules: dict, culture: Optional[str], exp: Expectations) -> None:
    if not culture:
        return
    key = culture.lower().replace(" ", "_")
    block = rules.get("culture_to_aesthetic", {}).get(key)
    if not block:
        return
    exp.metal_tones.extend(_expand_metals(block.get("metals", []), 3))
    for stone in block.get("stones", []):
        _add(exp.gem_categories, stone, 2)
    for kw in block.get("style_keywords", []):
        _add(exp.style_keywords, kw, 2)
    if block.get("energy"):
        exp.reasons.append(f"{culture} aesthetic → {block['energy']}")


def _from_personality(rules: dict, personality: Optional[str], exp: Expectations) -> None:
    if not personality:
        return
    key = personality.lower().replace(" ", "_")
    block = rules.get("personality_to_energy", {}).get(key)
    if not block:
        return
    exp.metal_tones.extend(_expand_metals(block.get("metals", []), 3))
    for stone in block.get("stones", []):
        _add(exp.gem_categories, stone, 2)
    for kw in block.get("style_keywords", []):
        _add(exp.style_keywords, kw, 3)
    if block.get("energy"):
        exp.reasons.append(f"{personality} → {block['energy']}")


def _psychology_for(occasion: Optional[str], rules: dict) -> Optional[str]:
    if not occasion:
        return None
    pb = rules.get("occasion_playbook", {}).get(occasion.lower())
    return pb.get("psychology") if pb else None


def derive_expectations(
    *,
    undertone: Optional[str] = None,
    surface_tone: Optional[str] = None,
    style_preference: Optional[str] = None,
    occasion: Optional[str] = None,
    category: Optional[str] = None,
    face_shape: Optional[str] = None,
    body_shape: Optional[str] = None,
    height_band: Optional[str] = None,
    finger_length: Optional[str] = None,
    birth_month: Optional[int] = None,
    cultural_background: Optional[str] = None,
    personality: Optional[str] = None,
) -> Expectations:
    """Build an Expectations bag from any subset of the 16 styling axes.

    Missing axes contribute nothing — no false signal. The returned
    Expectations can be queried with `.weight_for(value, dimension)` to score
    a candidate piece.
    """
    rules = _load_rules()
    exp = Expectations()

    # Undertone is the spine of metal selection. Fall back from surface_tone
    # if explicit undertone wasn't provided.
    effective_undertone = undertone
    if not effective_undertone and surface_tone:
        effective_undertone = _SURFACE_TO_UNDERTONE.get(surface_tone.lower())

    _from_undertone(rules, effective_undertone, exp)
    _from_surface_tone(rules, surface_tone, exp)
    _from_face_shape(rules, face_shape, category, exp)
    _from_body_shape(rules, body_shape, exp)
    _from_height(rules, height_band, exp)
    _from_finger_length(rules, finger_length, category, exp)
    _from_birth_month(rules, birth_month, exp)
    _from_culture(rules, cultural_background, exp)
    _from_personality(rules, personality, exp)

    if style_preference:
        _add(exp.style_keywords, style_preference, 3)

    exp.psychology_category = _psychology_for(occasion, rules)

    if not any([
        exp.metal_tones,
        exp.gem_categories,
        exp.cuts,
        exp.style_keywords,
        exp.scale_keywords,
    ]):
        # Sparse profile: lean on universal-safe combos so we can still pick.
        for combo in rules.get("universal_safe_combinations", []):
            tone = _METAL_NAME_TO_TONE.get(combo.get("metal", "").lower())
            if tone:
                _add(exp.metal_tones, tone, 1)
            stone = combo.get("stone")
            if stone:
                _add(exp.gem_categories, stone, 1)
        if rules.get("universal_safe_combinations"):
            exp.reasons.append("universal-safe pairing")

    return exp


def occasion_playbook(occasion: Optional[str]) -> Optional[dict]:
    """Return the playbook entry for an occasion, or None."""
    if not occasion:
        return None
    return _load_rules().get("occasion_playbook", {}).get(occasion.lower())


def birthstone_for(month: int) -> Optional[str]:
    block = _load_rules().get("birth_month_to_stone", {}).get(str(int(month)))
    return block.get("primary") if block else None
