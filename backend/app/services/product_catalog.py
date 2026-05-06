"""Full-catalog profile-based matcher.

Mirrors services/noor_catalog.py but for the broader products.json catalog
(60 pieces across rings, bracelets, earrings, pendants, necklaces, tiaras,
waist adornments). Implements the v2.0 intelligence spec from Data.txt:

  - aesthetic_engine: skin_tone -> metal_tone, style_preference -> form
  - recommendation_engine.output_structure: primary + secondary + statement

Returns three picks structured by role so the model can present three layers
(perfect match, slight variation, bolder evolution) per Data.txt's brand
signature, instead of a flat list.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "products.json"
_CATALOG_CACHE: list[dict[str, Any]] | None = None

_CATEGORY_ALIASES = {
    "rings": "ring",
    "bracelets": "bracelet",
    "earring": "earrings",
    "pendants": "pendant",
    "necklaces": "necklace",
    "tiaras": "tiara",
    "waist": "waist_adornment",
    "waist chain": "waist_adornment",
    "waist adornment": "waist_adornment",
    "waist-adornment": "waist_adornment",
}

_OCCASION_KEYWORDS = {
    "love": ["love", "devotion", "intimate", "connection", "embrace", "heart", "bond"],
    "anniversary": ["anniversary", "enduring", "commitment", "eternal", "lasting"],
    "gift": ["gift", "celebration", "occasion"],
    "self_reward": ["self", "personal", "individual", "achievement", "milestone"],
    "legacy": ["heritage", "legacy", "heirloom", "generational", "royal", "sovereign"],
    "status": ["status", "authority", "command", "elite", "exclusive", "definitive"],
    "milestone": ["milestone", "significant", "definitive", "landmark"],
    "everyday": ["daily", "everyday", "wearable", "versatile", "foundational"],
    "celebration": ["celebration", "festive", "imperial"],
}

_BOLD_STYLES = {"statement", "heritage"}


def _load() -> list[dict[str, Any]]:
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE
    try:
        with _CATALOG_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
        _CATALOG_CACHE = data.get("pieces", [])
    except Exception as exc:
        logger.error(f"Failed to load product catalog: {exc}")
        _CATALOG_CACHE = []
    return _CATALOG_CACHE


def _normalize_category(category: Optional[str]) -> Optional[str]:
    if not category:
        return None
    c = category.strip().lower()
    return _CATEGORY_ALIASES.get(c, c)


def _metal_score(piece_tone: Optional[str], skin_tone: Optional[str]) -> int:
    """Skin-tone -> metal mapping per Data.txt aesthetic_engine.skin_tone_logic."""
    if not skin_tone or not piece_tone:
        return 0
    skin = skin_tone.lower()
    tone = piece_tone.lower()
    if skin == "neutral":
        return 2
    if skin == tone:
        return 4
    if tone == "neutral":
        return 2
    return 0


def _style_score(piece_style: Optional[str], pref: Optional[str]) -> int:
    if not pref or not piece_style:
        return 0
    p = pref.lower()
    s = piece_style.lower()
    if p == s:
        return 4
    if p == "maximalist" and s == "statement":
        return 3
    if p == "minimal" and s == "minimalist":
        return 4
    return 0


def _occasion_score(piece: dict, occasion: Optional[str]) -> int:
    if not occasion:
        return 0
    text_parts = [piece.get("narrative", ""), piece.get("description", "")]
    notes = piece.get("design_notes", []) or []
    if isinstance(notes, list):
        text_parts.extend(str(n) for n in notes)
    text = " ".join(text_parts).lower()
    keys = _OCCASION_KEYWORDS.get(occasion.lower(), [occasion.lower()])
    return sum(2 for k in keys if k in text)


def _score(
    piece: dict,
    *,
    skin_tone: Optional[str],
    style: Optional[str],
    occasion: Optional[str],
) -> int:
    return (
        _metal_score(piece.get("metal_tone"), skin_tone)
        + _style_score(piece.get("style"), style)
        + _occasion_score(piece, occasion)
    )


def find_best_products(
    *,
    age: Optional[int] = None,  # reserved for future use; carried for API parity with noor_catalog
    skin_tone: Optional[str] = None,
    style_preference: Optional[str] = None,
    occasion: Optional[str] = None,
    category: Optional[str] = None,
) -> dict[str, Optional[dict]]:
    """Return three picks as {'primary', 'secondary', 'statement'}.

    primary    -> highest-score piece (perfect match)
    secondary  -> next-best with a different style or category (variation)
    statement  -> best-scoring 'statement' or 'heritage' piece (bolder evolution)
    """
    pieces = _load()
    if not pieces:
        return {"primary": None, "secondary": None, "statement": None}

    cat = _normalize_category(category)
    pool = [p for p in pieces if p.get("category") == cat] if cat else list(pieces)
    if cat and not pool:
        pool = list(pieces)

    scored = sorted(
        (
            (
                _score(p, skin_tone=skin_tone, style=style_preference, occasion=occasion),
                p.get("price") or 0,
                p,
            )
            for p in pool
        ),
        key=lambda x: (-x[0], -x[1]),
    )

    primary = scored[0][2] if scored else None
    primary_name = primary.get("name") if primary else None

    secondary = None
    if primary is not None:
        for _s, _pr, p in scored[1:]:
            if p.get("name") == primary_name:
                continue
            if p.get("style") != primary.get("style") or p.get("category") != primary.get("category"):
                secondary = p
                break
        if secondary is None and len(scored) > 1:
            secondary = scored[1][2]

    statement = None
    chosen = {primary_name, secondary.get("name") if secondary else None}
    for _s, _pr, p in scored:
        if p.get("name") in chosen:
            continue
        if p.get("style") in _BOLD_STYLES:
            statement = p
            break
    if statement is None:
        priced = sorted(
            (p for _s, _pr, p in scored if p.get("name") not in chosen),
            key=lambda x: -(x.get("price") or 0),
        )
        statement = priced[0] if priced else None

    return {"primary": primary, "secondary": secondary, "statement": statement}
