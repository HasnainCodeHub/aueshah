"""Input validation and sanitization utilities."""
import re
from typing import Any, Optional

from agents import GuardrailFunctionOutput, RunContextWrapper, input_guardrail

from app.models.errors import InjectionDetected, ValidationError


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


# Clearly out-of-scope topics — coding, math, weather, news, sports, politics,
# recipes, general trivia, other brands. These are strong signals; subtler
# cases are handled in-character by the system prompt's SCOPE & GRACEFUL
# REDIRECTION section.
_OFF_TOPIC_PATTERNS = [
    r"(?i)\b(write|generate|code|debug|fix)\b.*\b(python|javascript|java|c\+\+|code|script|function|html|css|sql)\b",
    r"(?i)\b(python|javascript|java|c\+\+|typescript|golang|rust)\b.*\b(code|script|program|function)\b",
    r"(?i)\bsolve\b.*\b(equation|math|integral|derivative|algebra|calculus)\b",
    r"(?i)\bweather\b.*\b(today|tomorrow|forecast|in)\b",
    r"(?i)\bwhat('?s| is) the weather\b",
    r"(?i)\b(stock price|stock market|crypto|bitcoin|ethereum)\b",
    r"(?i)\b(football|cricket|basketball|soccer|nba|fifa|world cup|olympics)\b",
    r"(?i)\b(president|prime minister|election|politics|government policy)\b",
    r"(?i)\b(recipe|cook|bake)\b.*\b(for|how to)\b",
    r"(?i)\btell me a joke\b",
    r"(?i)\b(translate|translation)\b.*\b(to|from|into)\b",
    r"(?i)\b(cartier|tiffany|bulgari|harry winston|van cleef|chopard|graff)\b",
]


def detect_off_topic(text: str) -> bool:
    """Fast keyword check for clearly out-of-scope requests."""
    if not text:
        return False
    for pattern in _OFF_TOPIC_PATTERNS:
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


def _extract_text(agent_input: Any) -> str:
    """Best-effort extraction of the latest user text from Agents SDK input."""
    if isinstance(agent_input, str):
        return agent_input
    if isinstance(agent_input, list):
        for item in reversed(agent_input):
            if isinstance(item, dict) and item.get("role") == "user":
                content = item.get("content", "")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    return " ".join(
                        part.get("text", "")
                        for part in content
                        if isinstance(part, dict)
                    )
    return ""


@input_guardrail
async def injection_guardrail(
    ctx: RunContextWrapper[None],
    agent: Any,
    agent_input: Any,
) -> GuardrailFunctionOutput:
    """Agents SDK input guardrail — tripwires on prompt-injection patterns."""
    text = _extract_text(agent_input)
    tripped = bool(text) and detect_prompt_injection(text)
    return GuardrailFunctionOutput(
        output_info={"reason": "prompt_injection"} if tripped else {},
        tripwire_triggered=tripped,
    )


@input_guardrail
async def off_topic_guardrail(
    ctx: RunContextWrapper[None],
    agent: Any,
    agent_input: Any,
) -> GuardrailFunctionOutput:
    """Tripwires on clearly out-of-scope requests (code, weather, sports, etc.)."""
    text = _extract_text(agent_input)
    tripped = bool(text) and detect_off_topic(text)
    return GuardrailFunctionOutput(
        output_info={"reason": "off_topic"} if tripped else {},
        tripwire_triggered=tripped,
    )
