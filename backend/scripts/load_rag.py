"""Load Aueshah knowledge base into Qdrant.

Chunks and embeds three sources:
  - app/data/heritage.md      (split on `---`, one chunk per section)
  - app/data/products.json    (one chunk per non-Noor piece)
  - app/data/noor_catalog.json (one chunk per Noor piece — narrative lookup only;
                                structured profile matching still lives in
                                services/noor_catalog.py)

Run:
    cd backend
    python -m scripts.load_rag

Requires OPENAI_API_KEY and a reachable Qdrant (QDRANT_URL). Idempotent:
recreates the collection each run.
"""
from __future__ import annotations

import json
import logging
import re
import sys
import uuid
from pathlib import Path
from typing import Iterable

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

# Allow running as `python -m scripts.load_rag` from /backend
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config.settings import settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("load_rag")

DATA_DIR = ROOT / "app" / "data"
HERITAGE_FILE = DATA_DIR / "heritage.md"
PRODUCTS_FILE = DATA_DIR / "products.json"
NOOR_FILE = DATA_DIR / "noor_catalog.json"

EMBED_BATCH = 64


def _parse_heritage(text: str) -> list[dict]:
    """Split heritage.md on `---` separators. Each chunk may have `source:` and
    `topic:` header lines followed by body text."""
    chunks: list[dict] = []
    raw_sections = [s.strip() for s in text.split("\n---\n")]
    for section in raw_sections:
        if not section or section.startswith("# "):
            # Skip the title header block
            # (first section is the document title + preamble)
            body_lines = []
            for line in section.splitlines():
                if line.startswith("#"):
                    continue
                body_lines.append(line)
            body = "\n".join(body_lines).strip()
            if not body or body.lower().startswith("source:") is False and len(body) < 80:
                continue
        source = None
        topic = None
        body_lines = []
        for line in section.splitlines():
            m_src = re.match(r"^source:\s*(.+)$", line.strip(), re.I)
            m_top = re.match(r"^topic:\s*(.+)$", line.strip(), re.I)
            if m_src:
                source = m_src.group(1).strip()
            elif m_top:
                topic = m_top.group(1).strip()
            elif line.startswith("#"):
                continue
            else:
                body_lines.append(line)
        content = "\n".join(body_lines).strip()
        if not content:
            continue
        chunks.append(
            {
                "content": content,
                "source": source or "heritage.md",
                "topic": topic,
                "kind": "heritage",
            }
        )
    return chunks


def _product_doc(p: dict) -> str:
    parts = [
        p.get("name", ""),
        f"Category: {p.get('category', '')}",
        f"Metal: {p.get('metal', '')} ({p.get('metal_tone', '')})",
    ]
    stones = p.get("stones")
    if isinstance(stones, list) and stones:
        parts.append("Stones: " + ", ".join(stones))
    elif isinstance(stones, str) and stones:
        parts.append(f"Stones: {stones}")
    if p.get("style"):
        parts.append(f"Style: {p['style']}")
    if p.get("description"):
        parts.append(p["description"])
    if p.get("narrative"):
        parts.append(p["narrative"])
    notes = p.get("design_notes")
    if isinstance(notes, list) and notes:
        parts.append("Design notes: " + "; ".join(notes))
    return "\n".join(parts)


def _parse_products() -> list[dict]:
    data = json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))
    pieces = data.get("pieces", [])
    out: list[dict] = []
    for p in pieces:
        out.append(
            {
                "content": _product_doc(p),
                "source": p.get("url", "products.json"),
                "topic": f"{p.get('category', 'piece')}:{p.get('name', '')}",
                "kind": "product",
                "name": p.get("name"),
                "category": p.get("category"),
                "price": p.get("price"),
            }
        )
    return out


def _parse_noor() -> list[dict]:
    data = json.loads(NOOR_FILE.read_text(encoding="utf-8"))
    pieces = data.get("pieces", [])
    out: list[dict] = []
    for p in pieces:
        out.append(
            {
                "content": _product_doc(p),
                "source": p.get("url", "noor_catalog.json"),
                "topic": f"noor:{p.get('name', '')}",
                "kind": "noor",
                "name": p.get("name"),
                "category": p.get("category"),
            }
        )
    return out


def _embed(client: OpenAI, texts: list[str]) -> list[list[float]]:
    resp = client.embeddings.create(input=texts, model=settings.embedding_model)
    return [d.embedding for d in resp.data]


def _batched(items: list[dict], n: int) -> Iterable[list[dict]]:
    for i in range(0, len(items), n):
        yield items[i : i + n]


def main() -> None:
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is required")

    logger.info("Parsing knowledge sources…")
    chunks: list[dict] = []
    chunks.extend(_parse_heritage(HERITAGE_FILE.read_text(encoding="utf-8")))
    chunks.extend(_parse_products())
    chunks.extend(_parse_noor())
    logger.info("Parsed %d chunks total", len(chunks))

    qdrant = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
    )
    collection = settings.qdrant_collection
    logger.info("Recreating collection '%s' (dim=%d)", collection, settings.embedding_dim)
    qdrant.recreate_collection(
        collection_name=collection,
        vectors_config=qm.VectorParams(
            size=settings.embedding_dim, distance=qm.Distance.COSINE
        ),
    )

    openai_client = OpenAI(api_key=settings.openai_api_key)
    total = 0
    for batch in _batched(chunks, EMBED_BATCH):
        vectors = _embed(openai_client, [c["content"] for c in batch])
        points = [
            qm.PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "content": c["content"],
                    "source": c.get("source"),
                    "topic": c.get("topic"),
                    "kind": c.get("kind"),
                    "name": c.get("name"),
                    "category": c.get("category"),
                    "price": c.get("price"),
                },
            )
            for c, vec in zip(batch, vectors)
        ]
        qdrant.upsert(collection_name=collection, points=points)
        total += len(points)
        logger.info("Upserted %d / %d", total, len(chunks))

    logger.info("Done. %d points in '%s'.", total, collection)


if __name__ == "__main__":
    main()
