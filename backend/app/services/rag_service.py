"""RAG service for vector search and retrieval."""
import asyncio
import logging
from typing import List, Optional

from openai import AsyncOpenAI

from app.config.settings import settings
from app.models.schemas import RAGChunk
from app.models.errors import RAGUnavailable

logger = logging.getLogger(__name__)


class RAGService:
    """Vector store retrieval service."""

    def __init__(self):
        """Initialize RAG service (Qdrant + OpenAI embeddings client)."""
        try:
            from qdrant_client import AsyncQdrantClient
            self.client = AsyncQdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key if settings.qdrant_api_key else None,
            )
        except Exception as e:
            logger.warning(f"Qdrant initialization warning: {e}")
            self.client = None

        self.embeddings_client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def retrieve(self, query_embedding: List[float], top_k: int = 3) -> List[RAGChunk]:
        """
        Retrieve top-k chunks from vector store.

        Args:
            query_embedding: Query vector embedding
            top_k: Number of chunks to retrieve (max 3)

        Returns:
            List of RAGChunk objects
        """
        if self.client is None:
            logger.warning("RAG: Qdrant client not initialized")
            return []

        if not query_embedding:
            return []

        top_k = min(top_k, 3)  # Enforce max 3 chunks

        try:
            # Timeout for RAG retrieval
            async with asyncio.timeout(settings.rag_timeout_seconds):
                # For Phase 1, return empty list (actual Qdrant integration pending)
                # In production, this would query Qdrant:
                # results = await self.client.search(
                #     collection_name="knowledge",
                #     query_vector=query_embedding,
                #     limit=top_k,
                # )
                logger.info("RAG: Mock retrieval (no vector store configured yet)")
                return []

        except asyncio.TimeoutError:
            logger.warning(f"RAG timeout after {settings.rag_timeout_seconds}s")
            raise RAGUnavailable("RAG service timeout")
        except Exception as e:
            logger.error(f"RAG retrieval error: {e}")
            raise RAGUnavailable(f"RAG service error: {str(e)}")

    async def get_embeddings(self, text: str) -> Optional[List[float]]:
        """
        Generate embeddings for query text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None on error
        """
        try:
            response = await self.embeddings_client.embeddings.create(
                input=text,
                model=settings.embedding_model,
            )
            if response.data:
                return response.data[0].embedding
            return None
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            return None
