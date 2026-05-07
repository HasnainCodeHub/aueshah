"""One-shot script: add a `cut` tag to each ring in products.json.

Cut assignments are derived by hand from each piece's description, design
notes, and stones — they are NOT auto-derivable. Re-running is idempotent.

Engagement consultations rely on this tag — `finger_length -> cut` mapping
in styling_rules.json scores rings by cut.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ring name -> cut. Derived by inspecting descriptions:
#   - Brilliant-cut diamonds with no center stone => round
#   - Heart-cut center stone => heart (PDF doesn't enumerate heart,
#     but mapping it to 'oval' / 'pear' (feminine grace) is the closest fit;
#     keeping 'heart' as a literal cut tag for engineering, and it will fall
#     through to the round-class scoring)
#   - Architectural / geometric / sharp / unisex => princess (sharp brilliance)
#   - Botanical / soft / romantic / morganite-pink => oval (romantic / universal)
#   - Royal / center-stone / signet emerald or ruby => emerald (executive/royal)
#   - Multi-stone royal vintage => cushion (warm vintage)
_CUT_MAP = {
    "Ecliptia": "round",
    "Enchanted Bloom": "oval",
    "Eternal Wave": "heart",
    "Luxura Statement Ring": "princess",
    "Pulse Ring": "round",
    "Royal Opulence": "cushion",
    "Sovereign Crown Ring": "emerald",
    "Trinity Luxe Ring": "round",
    "Vera Forma": "princess",
    "Whisper Ring": "oval",
}


def main() -> int:
    catalog_path = Path(__file__).resolve().parent.parent / "app" / "data" / "products.json"
    with catalog_path.open(encoding="utf-8") as f:
        data = json.load(f)

    pieces = data.get("pieces", [])
    changed = 0

    for piece in pieces:
        if piece.get("category") != "ring":
            continue
        name = piece.get("name")
        cut = _CUT_MAP.get(name)
        if not cut:
            print(f"  warning: no cut mapping for ring '{name}'")
            continue
        if piece.get("cut") == cut:
            continue
        piece["cut"] = cut
        changed += 1
        print(f"  - {name}: cut={cut}")

    print(f"\n{changed} ring(s) tagged.")

    with catalog_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Written: {catalog_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
