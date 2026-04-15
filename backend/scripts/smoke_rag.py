"""Quick sanity check — exercise rag_service against the loaded collection."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.rag_service import RAGService  # noqa: E402


QUERIES = [
    "What is the warranty on an Aueshah piece?",
    "Tell me about the Noor Collection origin",
    "Looking for a rose gold ring with morganite",
    "How do refund windows work after 60 days?",
    "What does the Aueshah hallmark mean?",
]


async def main() -> None:
    rag = RAGService()
    for q in QUERIES:
        print(f"\n=== {q}")
        emb = await rag.get_embeddings(q)
        if not emb:
            print("  (no embedding)")
            continue
        chunks = await rag.retrieve(emb, top_k=3)
        if not chunks:
            print("  (no chunks)")
            continue
        for i, c in enumerate(chunks, 1):
            snippet = c.content.replace("\n", " ")[:160]
            print(f"  [{i}] score={c.relevance_score:.3f} src={c.source}")
            print(f"      {snippet}…")


if __name__ == "__main__":
    asyncio.run(main())
