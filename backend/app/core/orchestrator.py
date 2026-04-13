"""Main request orchestrator - coordinates all components."""
import asyncio
import logging
import time
import uuid
from typing import Tuple

from app.models.schemas import ChatRequest, ChatResponse, ContextMessage
from app.models.errors import ChatException
from app.core.intent_classifier import IntentClassifier
from app.core.prompt_builder import PromptBuilder
from app.services.ai_client import AIClient
from app.services.rag_service import RAGService
from app.services.failure_handler import FailureHandler
from app.config.settings import settings
from app.config.prompts import SYSTEM_PROMPT, SKILL_PROMPTS
from app.config.skills_registry import get_skill

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main request orchestrator."""

    def __init__(self):
        """Initialize orchestrator components."""
        self.intent_classifier = IntentClassifier()
        self.ai_client = AIClient()
        self.rag_service = RAGService()
        self.failure_handler = FailureHandler()

    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        """
        Handle a complete chat request.

        Args:
            request: ChatRequest with message and optional context

        Returns:
            ChatResponse with reply
        """
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        logger.info(
            f"Chat request received",
            extra={
                "component": "orchestrator",
                "request_id": request_id,
                "message_length": len(request.message),
            },
        )

        try:
            # Step 1: Classify intent
            skill_name, confidence, routing_source = await self.intent_classifier.classify(
                request.message
            )

            # Step 2: Get skill definition
            skill_def = get_skill(skill_name)
            if not skill_def:
                skill_name = "general"
                skill_def = get_skill("general")

            # Step 3: Retrieve RAG chunks if skill requires it
            rag_chunks = []
            if skill_def.use_rag and settings.enable_rag:
                try:
                    # Get embeddings for message
                    embeddings = await self.rag_service.get_embeddings(request.message)
                    if embeddings:
                        rag_chunks = await self.rag_service.retrieve(embeddings, top_k=3)
                except Exception as e:
                    logger.warning(f"RAG retrieval failed: {e}, continuing without RAG")
                    rag_chunks = []

            # Step 4: Build prompt (system + skill + RAG + context + user)
            skill_prompt = SKILL_PROMPTS[skill_def.prompt_key]
            composed_user_message = PromptBuilder.build(
                system_prompt="",  # system handled separately below
                skill_prompt=skill_prompt,
                user_message=request.message,
                context=request.context,
                rag_chunks=rag_chunks,
            )

            # Step 5: Call AI
            reply = await self.ai_client.call_chat(
                system_prompt=SYSTEM_PROMPT,
                user_message=composed_user_message,
            )

            # Success
            latency_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"Chat response generated",
                extra={
                    "request_id": request_id,
                    "skill": skill_name,
                    "latency_ms": latency_ms,
                    "routing_source": routing_source,
                },
            )

            return ChatResponse(
                reply=reply,
                metadata={
                    "intent": skill_name,
                    "skill": skill_name,
                    "latency_ms": latency_ms,
                    "routing_source": routing_source,
                },
            )

        except ChatException as exc:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                f"Chat request failed: {exc.message}",
                extra={"request_id": request_id, "latency_ms": latency_ms},
            )
            raise

        except Exception as exc:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"Orchestrator error: {str(exc)}",
                extra={"request_id": request_id, "latency_ms": latency_ms},
                exc_info=True,
            )
            raise

