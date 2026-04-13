"""Failure handling and graceful degradation."""
import logging

from app.config.prompts import FALLBACK_RESPONSE
from app.models.errors import ChatException, RAGUnavailable, AIError

logger = logging.getLogger(__name__)


class FailureHandler:
    """Handle failures gracefully with fallback responses."""

    @staticmethod
    def handle_exception(exc: Exception) -> tuple[str, int]:
        """
        Handle exception and return safe fallback response.

        Args:
            exc: Exception to handle

        Returns:
            Tuple of (reply_text, http_code)
        """
        if isinstance(exc, ChatException):
            logger.warning(
                f"Chat exception: {exc.message}",
                extra={"component": "failure_handler", "error_code": exc.code},
            )
            return (exc.message, exc.code)

        elif isinstance(exc, RAGUnavailable):
            logger.warning(
                f"RAG unavailable: {exc.message}",
                extra={"component": "failure_handler"},
            )
            # RAG failure → continue without RAG (return fallback)
            return (FALLBACK_RESPONSE, 503)

        elif isinstance(exc, AIError):
            logger.error(
                f"AI error after retries: {exc.message}",
                extra={"component": "failure_handler"},
            )
            # AI failure after retries → return safe fallback
            return (FALLBACK_RESPONSE, 503)

        else:
            logger.error(
                f"Unexpected error: {str(exc)}",
                extra={"component": "failure_handler"},
                exc_info=True,
            )
            return ("An unexpected error occurred. Please try again.", 500)

    @staticmethod
    def get_fallback_reply() -> str:
        """Get safe fallback reply."""
        return FALLBACK_RESPONSE
