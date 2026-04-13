"""OpenAI API client with retry logic."""
import asyncio
import logging
from typing import Optional

from openai import AsyncOpenAI, APIError, APITimeoutError

from app.config.settings import settings
from app.models.errors import AITimeout, AIError

logger = logging.getLogger(__name__)


class AIClient:
    """Async OpenAI API client with retry and backoff."""

    def __init__(self):
        """Initialize OpenAI async client."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.max_retries = settings.max_retries if settings.enable_retry else 1

    async def call_chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.0,
    ) -> Optional[str]:
        """
        Call OpenAI Chat API with retry logic.

        Args:
            system_prompt: System prompt for behavior control
            user_message: User message to respond to
            temperature: Temperature for response generation

        Returns:
            Reply text or None on failure
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        backoff_ms = [100, 500]  # Retry backoffs in milliseconds
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=500,
                    ),
                    timeout=settings.chat_timeout_seconds - 0.5,  # Leave margin
                )

                if response.choices and response.choices[0].message:
                    reply = response.choices[0].message.content
                    logger.info(
                        f"AI call success on attempt {attempt + 1}",
                        extra={"component": "ai_client", "attempt": attempt + 1},
                    )
                    return reply

                logger.warning("AI response empty")
                last_error = AIError("Empty response from AI")

            except APITimeoutError as e:
                last_error = AITimeout(str(e))
                logger.warning(
                    f"AI timeout on attempt {attempt + 1}",
                    extra={"component": "ai_client", "attempt": attempt + 1},
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(backoff_ms[min(attempt, len(backoff_ms) - 1)] / 1000)

            except APIError as e:
                last_error = AIError(str(e))
                logger.warning(
                    f"AI API error on attempt {attempt + 1}: {e}",
                    extra={"component": "ai_client", "attempt": attempt + 1},
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(backoff_ms[min(attempt, len(backoff_ms) - 1)] / 1000)

            except asyncio.TimeoutError:
                last_error = AITimeout("Request timeout")
                logger.warning(f"Request timeout on attempt {attempt + 1}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(backoff_ms[min(attempt, len(backoff_ms) - 1)] / 1000)

        # All retries exhausted
        logger.error(f"AI call failed after {self.max_retries} attempts: {last_error}")
        raise last_error if last_error else AIError("AI request failed")
