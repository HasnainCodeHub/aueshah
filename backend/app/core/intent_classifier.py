"""Hybrid rule-based + LLM intent classification."""
import asyncio
import logging
import re
import yaml
from typing import Tuple, Optional

from app.services.ai_client import AIClient
from app.config.settings import settings

logger = logging.getLogger(__name__)


class IntentClassifier:
    """Classify user intent using rules first, LLM fallback."""

    def __init__(self):
        """Initialize classifier with routing rules."""
        self.ai_client = AIClient()
        self.rules = self._load_routing_rules()

    def _load_routing_rules(self) -> dict:
        """Load routing rules from YAML config."""
        try:
            with open("app/config/routing_rules.yaml", "r") as f:
                config = yaml.safe_load(f)
                return config.get("skills", {})
        except Exception as e:
            logger.warning(f"Failed to load routing rules: {e}, using defaults")
            return {
                "product": {"keywords": [], "patterns": []},
                "compare": {"keywords": [], "patterns": []},
                "noor": {"keywords": ["noor"], "patterns": []},
                "bespoke": {"keywords": ["custom", "bespoke"], "patterns": []},
                "general": {"keywords": [], "patterns": []},
            }

    async def classify(self, message: str) -> Tuple[str, float, str]:
        """
        Classify intent into one of 5 skills.

        Args:
            message: User message to classify

        Returns:
            Tuple of (skill_name, confidence, source) where source is "rule" or "llm"
        """
        # Step 1: Try rule-based classification
        skill_name, confidence = self._classify_by_rules(message)
        if skill_name != "general":  # If we found a non-fallback match
            logger.info(
                f"Intent classified by rules: {skill_name}",
                extra={
                    "component": "intent_classifier",
                    "intent": skill_name,
                    "source": "rule",
                    "confidence": confidence,
                },
            )
            return (skill_name, confidence, "rule")

        # Step 2: LLM fallback for ambiguous cases
        try:
            async with asyncio.timeout(settings.routing_timeout_ms / 1000):
                skill_name, confidence = await self._classify_by_llm(message)
                logger.info(
                    f"Intent classified by LLM: {skill_name}",
                    extra={
                        "component": "intent_classifier",
                        "intent": skill_name,
                        "source": "llm",
                        "confidence": confidence,
                    },
                )
                return (skill_name, confidence, "llm")
        except asyncio.TimeoutError:
            logger.warning("LLM classification timeout, using general skill")
            return ("general", 0.5, "llm_timeout")
        except Exception as e:
            logger.error(f"LLM classification error: {e}, using general skill")
            return ("general", 0.5, "llm_error")

    def _classify_by_rules(self, message: str) -> Tuple[str, float]:
        """
        Classify by matching keywords and regex patterns.

        Returns:
            Tuple of (skill_name, confidence score 0-1)
        """
        message_lower = message.lower()

        # Check each skill in order (except general)
        for skill_name in ["product", "compare", "noor", "bespoke"]:
            rules = self.rules.get(skill_name, {})
            keywords = rules.get("keywords", [])
            patterns = rules.get("patterns", [])

            # Check keywords
            for keyword in keywords:
                if keyword.lower() in message_lower:
                    return (skill_name, 0.9)

            # Check regex patterns
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return (skill_name, 0.85)

        # No match → fallback to general
        return ("general", 0.5)

    async def _classify_by_llm(self, message: str) -> Tuple[str, float]:
        """
        Classify using lightweight LLM call.

        Returns:
            Tuple of (skill_name, confidence)
        """
        prompt = f"""TASK: Classify user intent into exactly ONE of: [product, compare, noor, bespoke, general]

RULES:
1. Return ONLY valid JSON: {{"intent": "<one of above>", "confidence": <0.0-1.0>}}
2. Choose "general" if intent is ambiguous or none apply.
3. Never return unknown intents.

MESSAGE: "{message}"
"""

        try:
            response = await self.ai_client.call_chat(
                system_prompt="You are a deterministic intent classifier. Return only valid JSON with no other text.",
                user_message=prompt,
                temperature=0.0,
            )

            import json

            data = json.loads(response)
            intent = data.get("intent", "general").lower()
            confidence = float(data.get("confidence", 0.5))

            # Validate intent
            if intent not in ["product", "compare", "noor", "bespoke", "general"]:
                intent = "general"

            return (intent, confidence)

        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            raise
