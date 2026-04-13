"""Input validation and sanitization utilities."""
import re
from typing import Optional
from app.models.errors import ValidationError, InjectionDetected


def sanitize_input(text: str) -> str:
    """Sanitize user input: strip whitespace, validate length."""
    if not text:
        raise ValidationError("Message cannot be empty")

    text = text.strip()
    if not text:
        raise ValidationError("Message cannot be empty")

    if len(text) > 5000:
        raise ValidationError("Message exceeds maximum length (5000 characters)")

    return text


def detect_prompt_injection(text: str) -> bool:
    """Detect common prompt injection patterns."""
    injection_patterns = [
        r"(?i)ignore.*previous.*instruction",
        r"(?i)forget.*everything",
        r"(?i)system.*prompt",
        r"(?i)override.*instruction",
        r"(?i)disregard.*instruction",
        r"(?i)execute.*command",
        r"(?i)eval\(",
        r"(?i)exec\(",
    ]

    for pattern in injection_patterns:
        if re.search(pattern, text):
            return True

    return False


def validate_context(context: Optional[list]) -> Optional[list]:
    """Validate conversation context array."""
    if context is None:
        return None

    if not isinstance(context, list):
        raise ValidationError("Context must be an array")

    if len(context) > 15:
        # Truncate to last 15 messages
        context = context[-15:]

    for i, msg in enumerate(context):
        if not isinstance(msg, dict):
            raise ValidationError(f"Context message {i} must be an object")

        if "role" not in msg or "content" not in msg:
            raise ValidationError(f"Context message {i} must have 'role' and 'content'")

        if msg["role"] not in ("user", "assistant"):
            raise ValidationError(f"Context message {i} has invalid role: {msg['role']}")

        if not isinstance(msg["content"], str) or not msg["content"]:
            raise ValidationError(f"Context message {i} content must be non-empty string")

    return context
