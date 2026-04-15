"""Noor Collection catalog loader + profile-based matcher.

Loads noor_catalog.json (sample placeholder data for now) and exposes a simple
filter that maps the user profile onto the Aueshah aesthetic engine in
Data.txt — skin tone → metal, style preference → form, age tier → category fit,
occasion tags → emotional fit.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "noor_catalog.json"
_CATALOG_CACHE: list[dict[str, Any]] | None = None


def _load() -> list[dict[str, Any]]:
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE
    try:
        with _CATALOG_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
        _CATALOG_CACHE = data.get("pieces", [])
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to load Noor catalog: {exc}")
        _CATALOG_CACHE = []
    return _CATALOG_CACHE


def _age_to_tier(age: int | None) -> str | None:
    if age is None:
        return None
    if age < 30:
        return "young"
    if age < 50:
        return "established"
    return "mature"


def _score(
    piece: dict[str, Any],
    *,
    metal_tone: str | None,
    style: str | None,
    age_tier: str | None,
    occasion: str | None,
) -> int:
    score = 0
    if metal_tone and piece.get("metal_tone") == metal_tone:
        score += 3
    if metal_tone == "neutral" and piece.get("metal_tone") == "neutral":
        score += 3
    if style and piece.get("style") == style:
        score += 3
    if age_tier and age_tier in (piece.get("age_tier") or []):
        score += 2
    if occasion and occasion in (piece.get("occasion") or []):
        score += 2
    return score


def find_best_noor_pieces(
    *,
    age: int | None = None,
    skin_tone: str | None = None,
    style_preference: str | None = None,
    occasion: str | None = None,
    category: str | None = None,
    top_k: int = 2,
) -> list[dict[str, Any]]:
    """Return the top matching Noor pieces for a client profile.

    Args:
        age: numeric age if known (used to derive age_tier).
        skin_tone: "cool" | "warm" | "neutral" (maps to metal_tone).
        style_preference: "minimalist" | "statement" | "heritage" | "modern".
        occasion: free-form occasion tag (love, legacy, gift, self_reward, ...).
        category: optional piece category filter (ring, bracelet, pendant, earrings).
        top_k: how many top matches to return.
    """
    pieces = _load()
    if not pieces:
        return []

    metal_tone = skin_tone.lower() if skin_tone else None
    style = style_preference.lower() if style_preference else None
    age_tier = _age_to_tier(age)

    pool = pieces
    if category:
        pool = [p for p in pool if p.get("category") == category.lower()]
        if not pool:
            pool = pieces  # fall back to full pool if category too restrictive

    ranked = sorted(
        pool,
        key=lambda p: _score(
            p,
            metal_tone=metal_tone,
            style=style,
            age_tier=age_tier,
            occasion=occasion.lower() if occasion else None,
        ),
        reverse=True,
    )
    # Only return items that actually matched something
    matched = [p for p in ranked if _score(
        p,
        metal_tone=metal_tone,
        style=style,
        age_tier=age_tier,
        occasion=occasion.lower() if occasion else None,
    ) > 0]
    return matched[:top_k] if matched else ranked[:top_k]
