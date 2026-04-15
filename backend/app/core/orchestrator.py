"""Thin wrapper around the Agents SDK runner.

All intent classification, prompt composition, and model invocation now live
inside the Agents SDK. This orchestrator only translates our ChatRequest into
the SDK's input shape and maps the result back to ChatResponse.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from agents import Runner
from agents.exceptions import InputGuardrailTripwireTriggered

from app.core.agents_factory import build_triage_agent
from app.models.errors import ChatException, InjectionDetected, OffTopic
from app.models.schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinates a single chat turn through the Agents SDK."""

    def __init__(self) -> None:
        self.triage_agent = build_triage_agent()

    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        logger.info(
            "Chat request received",
            extra={
                "component": "orchestrator",
                "request_id": request_id,
                "message_length": len(request.message),
            },
        )

        try:
            input_items = self._build_input(request)

            result = await Runner.run(self.triage_agent, input_items)

            latency_ms = int((time.time() - start_time) * 1000)
            active_skill = self._infer_active_skill(result)

            logger.info(
                "Chat response generated",
                extra={
                    "request_id": request_id,
                    "skill": active_skill,
                    "latency_ms": latency_ms,
                },
            )

            return ChatResponse(
                reply=str(result.final_output).strip(),
                metadata={
                    "intent": active_skill,
                    "skill": active_skill,
                    "latency_ms": latency_ms,
                    "routing_source": "agents_sdk",
                },
            )

        except InputGuardrailTripwireTriggered as exc:
            latency_ms = int((time.time() - start_time) * 1000)
            reason = self._guardrail_reason(exc)
            logger.warning(
                f"Input guardrail tripped: {reason}",
                extra={"request_id": request_id, "latency_ms": latency_ms, "reason": reason},
            )
            if reason == "off_topic":
                raise OffTopic("off_topic")
            raise InjectionDetected("Invalid input detected")

        except ChatException:
            raise

        except Exception as exc:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"Orchestrator error: {exc}",
                extra={"request_id": request_id, "latency_ms": latency_ms},
                exc_info=True,
            )
            raise

    @staticmethod
    def _build_input(request: ChatRequest) -> list[dict[str, Any]]:
        """Translate ChatRequest.context + message into SDK input_items.

        The Agents SDK accepts a list of {role, content} items — the same shape
        we already receive from the client. We append the new user message at
        the end.
        """
        items: list[dict[str, Any]] = []
        if request.context:
            for msg in request.context:
                items.append({"role": msg.role, "content": msg.content})
        items.append({"role": "user", "content": request.message})
        return items

    @staticmethod
    def _guardrail_reason(exc: InputGuardrailTripwireTriggered) -> str:
        """Best-effort extraction of the guardrail reason for routing redirects."""
        try:
            result = getattr(exc, "guardrail_result", None)
            output = getattr(result, "output", None) if result is not None else None
            info = getattr(output, "output_info", None) if output is not None else None
            if isinstance(info, dict):
                return str(info.get("reason", "")) or "unknown"
        except Exception:  # noqa: BLE001 — best-effort metadata read
            pass
        return "unknown"

    @staticmethod
    def _infer_active_skill(result: Any) -> str:
        """Best-effort: read the last agent that produced the final output."""
        try:
            last_agent = getattr(result, "last_agent", None)
            if last_agent is not None and getattr(last_agent, "name", None):
                return last_agent.name
        except Exception:  # noqa: BLE001 — metadata is non-critical
            pass
        return "general"
