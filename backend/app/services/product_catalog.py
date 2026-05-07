"""Full-catalog profile-based matcher.

Implements the v3.0 intelligence spec: skin_tone -> metal, style_preference ->
form, occasion -> narrative, plus 8 additional axes from the PDF
(`updated.pdf`): face shape, body shape, height, finger length, birth month,
cultural background, personality, surface tone. The styling engine
(`services/styling_engine.py`) converts any subset of these axes into graded
expectations a piece can be scored against; this module wraps it with the
catalog and returns three picks structured by role:

  primary    — perfect match (highest score)
  secondary  — slight variation (different style or category)
  statement  — bolder evolution (statement / heritage style or top-priced)

Each pick now carries a `reasons` array — a list of styling rationales the
agent can echo verbatim when presenting, instead of inventing.

Backward compatible: callers using only the v2 axes (skin_tone /
style_preference / occasion / category / age) get exactly the same outputs
they did before, plus a `reasons` field they can ignore.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from app.services.styling_engine import Expectations, derive_expectations

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
    "engagement": ["engagement", "promise", "love", "eternal", "devotion", "commitment"],
    "gift": ["gift", "celebration", "occasion"],
    "self_reward": ["self", "personal", "individual", "achievement", "milestone"],
    "legacy": ["heritage", "legacy", "heirloom", "generational", "royal", "sovereign"],
    "status": ["status", "authority", "command", "elite", "exclusive", "definitive"],
    "milestone": ["milestone", "significant", "definitive", "landmark"],
    "everyday": ["daily", "everyday", "wearable", "versatile", "foundational"],
    "celebration": ["celebration", "festive", "imperial"],
    "formal_event": ["statement", "imperial", "ceremonial", "festive"],
    "heritage_addition": ["heritage", "legacy", "heirloom", "royal", "sovereign"],
}

_BOLD_STYLES = {"statement", "heritage"}


# Crosswalk: catalog `stones` strings → canonical gem categories used by the
# styling engine. Catalog entries are descriptive ("brilliant-cut diamonds",
# "blue sapphires"); we normalise to "diamond", "sapphire", etc. for scoring.
_STONE_KEYWORDS = {
    "diamond": ["diamond"],
    "sapphire": ["sapphire"],
    "emerald": ["emerald"],
    "ruby": ["ruby"],
    "pearl": ["pearl"],
    "opal": ["opal"],
    "tanzanite": ["tanzanite"],
    "morganite": ["morganite"],
    "aquamarine": ["aquamarine"],
    "garnet": ["garnet"],
    "amethyst": ["amethyst"],
    "peridot": ["peridot"],
    "citrine": ["citrine"],
    "topaz": ["topaz"],
    "turquoise": ["turquoise"],
    "tourmaline": ["tourmaline"],
    "alexandrite": ["alexandrite"],
    "black_diamond": ["black diamond"],
    "champagne_diamond": ["champagne diamond"],
    "pink_sapphire": ["pink sapphire"],
    "jade": ["jade"],
}


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


def _piece_gem_categories(piece: dict) -> list[str]:
    """Derive canonical gem categories present in a piece's stones array."""
    stones_raw = " ".join(str(s) for s in piece.get("stones") or []).lower()
    found: list[str] = []
    for canon, kws in _STONE_KEYWORDS.items():
        if any(kw in stones_raw for kw in kws):
            found.append(canon)
    return found


# ---------- v2 scorers (kept verbatim for backward compatibility) ----------


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


# ---------- v3 scorers (engine-driven) ----------


def _expectation_metal_score(piece: dict, exp: Expectations) -> int:
    return exp.weight_for(piece.get("metal_tone"), "metal_tones")


def _expectation_gem_score(piece: dict, exp: Expectations) -> int:
    score = 0
    for cat in _piece_gem_categories(piece):
        score += exp.weight_for(cat, "gem_categories")
    return score


def _expectation_style_score(piece: dict, exp: Expectations) -> int:
    score = 0
    style = (piece.get("style") or "").lower()
    if style:
        score += exp.weight_for(style, "style_keywords")
    cut = (piece.get("cut") or "").lower()
    if cut:
        score += exp.weight_for(cut, "cuts")
    # Soft signal: style_keywords vs. piece narrative/description.
    text = " ".join([
        piece.get("narrative", ""),
        piece.get("description", ""),
        " ".join(str(n) for n in (piece.get("design_notes") or [])),
    ]).lower()
    for kw, w in exp.style_keywords:
        if kw in text:
            score += max(1, w // 2)
    return score


def _expectation_scale_penalty(piece: dict, exp: Expectations) -> int:
    """Negative for pieces that violate avoid_keywords; positive when scale fits."""
    text = " ".join([
        piece.get("style") or "",
        piece.get("narrative", ""),
        " ".join(str(n) for n in (piece.get("design_notes") or [])),
    ]).lower()
    score = 0
    for av in exp.avoid_keywords:
        if av in text:
            score -= 3
    for kw, w in exp.scale_keywords:
        if kw in text:
            score += w
    return score


def _birthstone_alignment_score(piece: dict, exp: Expectations) -> int:
    """Bonus when the piece's stones overlap with birth-month expectations."""
    if "birth_month_alignment" in piece:
        # Piece has been pre-tagged. Engine signals via gem_categories.
        primary = (piece.get("birth_month_alignment") or "").lower()
        if primary:
            return exp.weight_for(primary, "gem_categories")
    return 0


def _piece_reasons(piece: dict, exp: Expectations) -> list[str]:
    """Derive a short list of styling reasons that actually apply to THIS piece.

    Filters the engine's accumulated reasons to those whose underlying signal
    matched the piece. The agent uses this list verbatim when presenting.
    """
    out: list[str] = []
    style = (piece.get("style") or "").lower()
    cut = (piece.get("cut") or "").lower()
    metal_tone = (piece.get("metal_tone") or "").lower()
    gems = _piece_gem_categories(piece)

    for reason in exp.reasons:
        rl = reason.lower()
        if "undertone" in rl and metal_tone and metal_tone in rl.replace("yellow gold", "warm").replace("white gold", "cool"):
            out.append(reason)
            continue
        # Birth-month reasons mention the gem name directly.
        if "birth month" in rl and any(g in rl for g in gems):
            out.append(reason)
            continue
        # Finger / cut reasons mention the cut name directly.
        if "fingers" in rl and cut and cut in rl:
            out.append(reason)
            continue
        # Personality / culture / face reasons use style or scale keywords —
        # accept if the keyword shows up in style or narrative.
        if any(kw in rl for kw in ["aesthetic", "→ ", "personality"]):
            text = " ".join([style, piece.get("narrative", ""), piece.get("description", "")]).lower()
            tail = rl.split("→")[-1].strip()
            if tail and tail in text:
                out.append(reason)
                continue
        # Universal-safe fallback always applies.
        if "universal-safe" in rl:
            out.append(reason)

    # Deduplicate while preserving order.
    seen = set()
    deduped: list[str] = []
    for r in out:
        if r not in seen:
            seen.add(r)
            deduped.append(r)
    return deduped[:3]


def _score(
    piece: dict,
    *,
    skin_tone: Optional[str],
    style: Optional[str],
    occasion: Optional[str],
    exp: Expectations,
) -> int:
    return (
        _metal_score(piece.get("metal_tone"), skin_tone)
        + _style_score(piece.get("style"), style)
        + _occasion_score(piece, occasion)
        + _expectation_metal_score(piece, exp)
        + _expectation_gem_score(piece, exp)
        + _expectation_style_score(piece, exp)
        + _expectation_scale_penalty(piece, exp)
        + _birthstone_alignment_score(piece, exp)
    )


def _attach_reasons(piece: Optional[dict], exp: Expectations) -> Optional[dict]:
    if piece is None:
        return None
    reasons = _piece_reasons(piece, exp)
    if reasons:
        out = dict(piece)
        out["reasons"] = reasons
        return out
    return piece


def find_best_products(
    *,
    age: Optional[int] = None,
    skin_tone: Optional[str] = None,
    style_preference: Optional[str] = None,
    occasion: Optional[str] = None,
    category: Optional[str] = None,
    surface_tone: Optional[str] = None,
    face_shape: Optional[str] = None,
    body_shape: Optional[str] = None,
    height_band: Optional[str] = None,
    finger_length: Optional[str] = None,
    birth_month: Optional[int] = None,
    cultural_background: Optional[str] = None,
    personality: Optional[str] = None,
    budget_band: Optional[str] = None,
) -> dict[str, Optional[dict]]:
    """Return three picks as {'primary', 'secondary', 'statement'}.

    Each pick may include a `reasons` list — short styling rationales the
    agent can verbalize ("warm undertone → yellow gold", "May → emerald").
    Missing dimensions degrade gracefully via the styling engine's
    universal-safe-combinations fallback.

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

    exp = derive_expectations(
        undertone=skin_tone,
        surface_tone=surface_tone,
        style_preference=style_preference,
        occasion=occasion,
        category=cat,
        face_shape=face_shape,
        body_shape=body_shape,
        height_band=height_band,
        finger_length=finger_length,
        birth_month=birth_month,
        cultural_background=cultural_background,
        personality=personality,
    )

    scored = sorted(
        (
            (
                _score(
                    p,
                    skin_tone=skin_tone,
                    style=style_preference,
                    occasion=occasion,
                    exp=exp,
                ),
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

    return {
        "primary": _attach_reasons(primary, exp),
        "secondary": _attach_reasons(secondary, exp),
        "statement": _attach_reasons(statement, exp),
    }
