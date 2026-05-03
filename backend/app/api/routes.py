"""FastAPI routes for the chat API."""
import asyncio
import time
import uuid as uuid_mod
import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.config.prompts import OFF_TOPIC_RESPONSE
from app.models.schemas import ChatRequest, ChatResponse, ErrorResponse, AppointmentRequest, AppointmentResponse, cap_context
from app.models.errors import ValidationError, InjectionDetected, OffTopic
from app.utils.validators import sanitize_input, detect_prompt_injection, detect_off_topic
from app.core.orchestrator import Orchestrator
from app.core.personalization import build_preamble
from app.services.failure_handler import FailureHandler
from app.services.persistence_writer import persist_turn
from app.services.summary_cache import get_summary_cache
from app.services.profile_extractor import extract_profile_fields, diff_against_user
from app.middleware.rate_limiter import check_rate_limit
from app.auth.visitor import get_visitor_id, set_visitor_cookie
from app.core.agents_context import set_current_user_id
from app.auth.dependencies import get_current_user_optional
from app.db.session import get_session, get_session_factory
from app.db.repositories import chat_history as chat_repo
from app.db.repositories import users as user_repo
from app.services.appointment_workflow import create_appointment
from app.utils.metrics import (
    APPOINTMENT_REQUESTS_TOTAL,
    CHAT_LATENCY_SECONDS,
    CHAT_REQUESTS_TOTAL,
    RATE_LIMIT_HITS_TOTAL,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Singleton orchestrator
_orchestrator = None


def get_orchestrator() -> Orchestrator:
    """Get or create orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


async def _load_personalization(user) -> str | None:
    """Fetch recent history + last intent for an authenticated user and assemble the preamble.

    Cached per-user with short TTL so repeated turns within the same session
    don't re-summarize. Returns None if there's nothing personal to inject.
    """
    if user is None:
        return None

    cache = get_summary_cache()
    cached = cache.get(user.id)
    if cached is not None:
        return cached

    factory = get_session_factory()
    if factory is None:
        return build_preamble(user, recent_messages=[], last_intent=None)

    try:
        async with factory() as session:
            recent = await chat_repo.get_recent_for_user(session, user.id, limit=24)
            last_intent = await chat_repo.get_last_intent(session, user.id)
    except Exception:
        logger.warning("Failed to load personalization context — continuing", exc_info=True)
        return build_preamble(user, recent_messages=[], last_intent=None)

    preamble = build_preamble(user, recent_messages=recent, last_intent=last_intent)
    if preamble:
        cache.set(user.id, preamble)
    return preamble


async def _capture_profile_updates(user, message: str) -> None:
    """LLM-based profile fact extraction.

    Runs as a background task — calls the LLM to merge any new facts from
    the user's latest message into the JSONB profile_facts column. Never
    raises; logs failures and moves on.
    """
    from app.services.llm_profile_extractor import extract_and_merge

    factory = get_session_factory()
    if factory is None:
        return

    existing = user.profile_facts or {}
    new_facts = await extract_and_merge(message, existing)

    if new_facts == existing or not isinstance(new_facts, dict):
        return

    try:
        async with factory() as session:
            from sqlalchemy import update as _sql_update
            from app.db.models import User as _User
            await session.execute(
                _sql_update(_User)
                .where(_User.id == user.id)
                .values(profile_facts=new_facts)
            )
            await session.commit()
        get_summary_cache().invalidate(user.id)
        logger.info(
            "Profile facts updated via LLM",
            extra={"user_id": str(user.id), "fact_keys": sorted(new_facts.keys())},
        )
    except Exception:
        logger.warning("Failed to persist LLM-extracted profile facts", exc_info=True)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    user=Depends(get_current_user_optional),
):
    """
    POST /chat endpoint.

    Accepts a chat request with message and optional conversation context.
    Returns a reply from the AI concierge system.

    Args:
        request: ChatRequest with message and optional context

    Returns:
        ChatResponse with reply and metadata

    Raises:
        400: Validation error
        503: Service unavailable (AI/RAG timeout)
        500: Internal error
    """
    start = time.monotonic()
    intent_label = "unknown"
    result_label = "ok"
    try:
        # Step 0: Rate limit check (sliding window, per-IP)
        client_ip = http_request.client.host if http_request.client else "unknown"
        await check_rate_limit(client_ip)

        # Step 1: Validate message
        message = sanitize_input(request.message)

        # Step 2: Check for prompt injection
        if detect_prompt_injection(message):
            logger.warning("Prompt injection detected")
            raise InjectionDetected("Invalid input detected")

        # Step 3: Fast off-topic check — warm in-character redirect, not an error
        if detect_off_topic(message):
            logger.info("Off-topic request — returning warm redirect")
            return ChatResponse(
                reply=OFF_TOPIC_RESPONSE,
                metadata={"intent": "off_topic", "skill": "general", "routing_source": "guardrail"},
            )

        # Step 4: Defense-in-depth context cap
        capped_context = cap_context(request.context)

        # Step 5: Resolve visitor identity
        visitor_id = get_visitor_id(http_request)
        session_id = request.session_id or str(uuid_mod.uuid4())

        # Step 6: Set user context for agent tools + build personalization preamble
        set_current_user_id(user.id if user else None)
        personalization_preamble = await _load_personalization(user)

        # Step 6b: Build page-context line if the client sent page_context
        page_context_line = None
        if request.page_context:
            pc = request.page_context
            parts = [f"The visitor is currently on a {pc.page_type} page"]
            if pc.product_name:
                parts.append(f"viewing {pc.product_name}")
            if pc.collection_name:
                parts.append(f"in the {pc.collection_name} collection")
            page_context_line = "PAGE AWARENESS: " + ", ".join(parts) + "."

        # Step 7: Orchestrate request
        validated_request = ChatRequest(message=message, context=capped_context, session_id=session_id)
        response = await orchestrator.handle_chat(
            validated_request,
            personalization_preamble=personalization_preamble,
            page_context_line=page_context_line,
        )

        # Step 8: Persist chat turn (fire-and-forget — never blocks response)
        metadata = response.metadata or {}
        intent_label = metadata.get("intent") or "unknown"
        asyncio.create_task(persist_turn(
            user_id=user.id if user else None,
            visitor_id=uuid_mod.UUID(visitor_id),
            session_id=uuid_mod.UUID(session_id) if len(session_id) == 36 else uuid_mod.uuid4(),
            user_message=message,
            assistant_reply=response.reply,
            intent=metadata.get("intent"),
            skill=metadata.get("skill"),
            routing_source=metadata.get("routing_source"),
            latency_ms=metadata.get("latency_ms"),
        ))

        # Step 9: Capture profile updates from the user's message (auth only, fire-and-forget)
        if user is not None:
            asyncio.create_task(_capture_profile_updates(user, message))

        # Step 10: Set visitor cookie on response
        json_response = JSONResponse(content=response.model_dump())
        set_visitor_cookie(json_response, visitor_id)
        return json_response

    except ValidationError as e:
        result_label = "validation_error"
        logger.warning(f"Validation error: {e.message}")
        return JSONResponse(status_code=400, content=ErrorResponse(error=e.message, code=400).model_dump())

    except InjectionDetected as e:
        result_label = "injection"
        logger.warning(f"Injection detected: {e.message}")
        return JSONResponse(status_code=400, content=ErrorResponse(error=e.message, code=400).model_dump())

    except OffTopic:
        result_label = "off_topic"
        intent_label = "off_topic"
        logger.info("Off-topic guardrail tripped in Agents SDK — returning warm redirect")
        return ChatResponse(
            reply=OFF_TOPIC_RESPONSE,
            metadata={"intent": "off_topic", "skill": "general", "routing_source": "guardrail"},
        )

    except Exception as e:
        result_label = "error"
        reply, code = FailureHandler.handle_exception(e)
        return JSONResponse(status_code=code, content=ErrorResponse(error=reply, code=code).model_dump())

    finally:
        CHAT_LATENCY_SECONDS.observe(time.monotonic() - start)
        CHAT_REQUESTS_TOTAL.labels(intent=intent_label, result=result_label).inc()


@router.post("/appointment-request", response_model=AppointmentResponse)
async def request_appointment(
    request: AppointmentRequest,
    user=Depends(get_current_user_optional),
    session=Depends(get_session),
):
    """
    POST /appointment-request endpoint.

    Persists the request to the appointments table and fires SendGrid
    notifications fire-and-forget. Falls back to a logged-only flow if the
    database is unavailable so the chat surface never hard-fails.
    """
    try:
        if session is not None:
            row = await create_appointment(
                session,
                email=request.email,
                appointment_type=request.appointment_type,
                user_id=user.id if user else None,
                phone=request.phone,
                preferred_date=request.preferred_date,
                notes=request.notes,
            )
            reference_id = row.reference_id
            APPOINTMENT_REQUESTS_TOTAL.labels(appointment_type=request.appointment_type).inc()
        else:
            # DB not configured (dev/test) — keep the legacy log-only path so
            # the concierge surface still answers gracefully.
            reference_id = f"APT-{uuid_mod.uuid4().hex[:8].upper()}"
            logger.warning(
                "Appointment request without DB",
                extra={"reference_id": reference_id, "email": request.email},
            )

        return AppointmentResponse(
            status="success",
            message=(
                f"Thank you! We've received your request (Ref: {reference_id}). "
                f"Our concierge team will contact you at {request.email} within 24 hours to confirm your appointment."
            ),
            reference_id=reference_id,
        )

    except Exception as e:
        logger.error(f"Appointment request error: {e}", exc_info=True)
        return AppointmentResponse(
            status="error",
            message="We encountered an issue processing your request. Please contact service@aueshah.com directly.",
        )


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
