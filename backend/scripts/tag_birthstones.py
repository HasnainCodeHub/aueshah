"""One-shot script: derive `birth_month_alignment` for each catalog piece
based on its `stones` array, and rewrite products.json in place.

Idempotent — running it twice yields the same result. Safe to re-run after
catalog edits.

Usage:
  uv run python -m scripts.tag_birthstones        # writes products.json
  uv run python -m scripts.tag_birthstones --dry  # prints diff, no write
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Map birthstone names -> (canonical_name, month).
# Ordered so primary birthstones win over alternates when a piece has multiple.
_BIRTHSTONE_MAP = [
    ("garnet", "garnet", 1),
    ("amethyst", "amethyst", 2),
    ("aquamarine", "aquamarine", 3),
    ("diamond", "diamond", 4),
    ("emerald", "emerald", 5),
    ("pearl", "pearl", 6),
    ("alexandrite", "alexandrite", 6),
    ("ruby", "ruby", 7),
    ("peridot", "peridot", 8),
    ("sapphire", "sapphire", 9),
    ("opal", "opal", 10),
    ("tourmaline", "tourmaline", 10),
    ("citrine", "citrine", 11),
    ("topaz", "topaz", 11),
    ("tanzanite", "tanzanite", 12),
    ("turquoise", "turquoise", 12),
]


def derive_alignment(stones: list[str]) -> dict | None:
    """Return {"stone": canonical, "month": int} for the strongest birthstone
    match in the piece's stones array, or None if no birthstone is present.

    "diamond" is excluded as a birth-month signal because virtually every
    Aueshah piece carries diamonds — it would over-tag the catalog as April.
    Only assign April when diamond is the SOLE stone.
    """
    text = " ".join(str(s).lower() for s in stones)
    if not text.strip():
        return None

    matches: list[tuple[str, int]] = []
    for _kw, canon, month in _BIRTHSTONE_MAP:
        if _kw in text and (canon, month) not in matches:
            matches.append((canon, month))

    # Drop diamond unless it's the only matched stone.
    non_diamond = [m for m in matches if m[0] != "diamond"]
    if non_diamond:
        # Prefer the first non-diamond birthstone for a deterministic pick.
        canon, month = non_diamond[0]
        return {"stone": canon, "month": month}
    if matches:
        canon, month = matches[0]
        return {"stone": canon, "month": month}
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true", help="Print proposed changes; do not write.")
    args = parser.parse_args()

    catalog_path = Path(__file__).resolve().parent.parent / "app" / "data" / "products.json"
    with catalog_path.open(encoding="utf-8") as f:
        data = json.load(f)

    pieces = data.get("pieces", [])
    changed = 0
    additions: list[tuple[str, dict]] = []

    for piece in pieces:
        alignment = derive_alignment(piece.get("stones") or [])
        existing = piece.get("birth_month_alignment")
        if alignment is None:
            if existing:
                piece.pop("birth_month_alignment", None)
                changed += 1
                additions.append((piece["name"], {"removed": existing}))
            continue
        # Compare existing stone+month to the derived one.
        if not isinstance(existing, dict) or existing.get("month") != alignment["month"]:
            piece["birth_month_alignment"] = alignment["stone"]  # store stone name; engine reads canonical
            piece["birth_month"] = alignment["month"]
            changed += 1
            additions.append((piece["name"], alignment))
        else:
            # Already correct — ensure both fields are present in canonical form.
            piece["birth_month_alignment"] = alignment["stone"]
            piece["birth_month"] = alignment["month"]

    print(f"{changed} piece(s) updated.")
    for name, info in additions:
        print(f"  - {name}: {info}")

    if args.dry:
        print("\n(dry run — no file written)")
        return 0

    with catalog_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"\nWritten: {catalog_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
