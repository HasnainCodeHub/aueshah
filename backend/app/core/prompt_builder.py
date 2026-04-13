"""Prompt assembly from components."""
import logging
from typing import List, Optional

from app.config.prompts import SYSTEM_PROMPT
from app.models.schemas import RAGChunk, ContextMessage
from app.skills.base import Skill

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Assemble multi-part prompts from system, skill, RAG, and context.

    COMPOSITION ORDER (prevents duplication and hallucination):
    1. system_prompt      - Brand brain, core rules
    2. skill_prompt       - Skill-specific responsibility
    3. rag_chunks         - Context grounding (if skill.use_rag)
    4. conversation_context - Last 10-15 messages
    5. current_message    - User input

    IMPORTANT: Do not repeat rules from system_prompt in skill_prompt.
    Each layer has distinct responsibility; avoid duplication.
    """

    @staticmethod
    def build(
        system_prompt: str,
        skill_prompt: str,
        user_message: str,
        context: Optional[List[ContextMessage]] = None,
        rag_chunks: Optional[List[RAGChunk]] = None,
    ) -> str:
        """
        Build complete prompt for AI call following strict composition order.

        Args:
            system_prompt: System/brand brain prompt (mandatory rules)
            skill_prompt: Skill-specific instructions (responsibility + constraints)
            user_message: Current user message
            context: Conversation context (last N messages)
            rag_chunks: Retrieved knowledge chunks (max 3 per spec)

        Returns:
            Complete prompt string assembled in composition order
        """
        parts = []

        # 1. System prompt (brand brain)
        parts.append(system_prompt)

        # 2. Skill-specific instructions
        parts.append(f"\n{skill_prompt}")

        # 3. RAG context (if available)
        if rag_chunks and len(rag_chunks) > 0:
            parts.append("\n\n### Context from Knowledge Base:")
            for i, chunk in enumerate(rag_chunks[:3], 1):  # Max 3 chunks
                parts.append(f"\n[Context {i}]: {chunk.content}")
                if chunk.source:
                    parts.append(f"(Source: {chunk.source})")

        # 4. Conversation context (if available)
        if context and len(context) > 0:
            parts.append("\n\n### Conversation History:")
            for msg in context[-15:]:  # Last 15 messages
                role = msg.role.upper()
                parts.append(f"\n{role}: {msg.content}")

        # 5. Current user message
        parts.append(f"\n\nUSER: {user_message}\n\nASSISTANT:")

        prompt = "".join(parts)

        logger.info(
            "Prompt built",
            extra={
                "component": "prompt_builder",
                "prompt_length": len(prompt),
                "rag_chunks": len(rag_chunks) if rag_chunks else 0,
                "context_messages": len(context) if context else 0,
            },
        )

        return prompt
