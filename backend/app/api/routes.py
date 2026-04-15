"""FastAPI routes for the chat API."""
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.config.prompts import OFF_TOPIC_RESPONSE
from app.models.schemas import ChatRequest, ChatResponse, ErrorResponse, AppointmentRequest, AppointmentResponse
from app.models.errors import ValidationError, InjectionDetected, OffTopic
from app.utils.validators import sanitize_input, detect_prompt_injection, detect_off_topic
from app.core.orchestrator import Orchestrator
from app.services.failure_handler import FailureHandler

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


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, orchestrator: Orchestrator = Depends(get_orchestrator)):
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
    try:
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

        # Step 4: Orchestrate request (context already validated by Pydantic schema)
        validated_request = ChatRequest(message=message, context=request.context)
        response = await orchestrator.handle_chat(validated_request)

        return response

    except ValidationError as e:
        logger.warning(f"Validation error: {e.message}")
        return JSONResponse(status_code=400, content=ErrorResponse(error=e.message, code=400).model_dump())

    except InjectionDetected as e:
        logger.warning(f"Injection detected: {e.message}")
        return JSONResponse(status_code=400, content=ErrorResponse(error=e.message, code=400).model_dump())

    except OffTopic:
        logger.info("Off-topic guardrail tripped in Agents SDK — returning warm redirect")
        return ChatResponse(
            reply=OFF_TOPIC_RESPONSE,
            metadata={"intent": "off_topic", "skill": "general", "routing_source": "guardrail"},
        )

    except Exception as e:
        reply, code = FailureHandler.handle_exception(e)
        return JSONResponse(status_code=code, content=ErrorResponse(error=reply, code=code).model_dump())


@router.post("/appointment-request", response_model=AppointmentResponse)
async def request_appointment(request: AppointmentRequest):
    """
    POST /appointment-request endpoint.

    Captures appointment requests from clients (email, phone, preferred date, notes).
    The concierge team will contact the client within 24 hours.

    Args:
        request: AppointmentRequest with email, phone, appointment_type, notes

    Returns:
        AppointmentResponse with confirmation and reference ID
    """
    try:
        # Generate reference ID for tracking
        import uuid
        from datetime import datetime
        reference_id = f"APT-{uuid.uuid4().hex[:8].upper()}"

        # Log the appointment request (in real system, this would save to database/CRM)
        logger.info(
            f"Appointment requested: {reference_id} | "
            f"Type: {request.appointment_type} | Email: {request.email}"
        )

        # Return confirmation to client
        return AppointmentResponse(
            status="success",
            message=(
                f"Thank you! We've received your request (Ref: {reference_id}). "
                f"Our concierge team will contact you at {request.email} within 24 hours to confirm your appointment."
            ),
            reference_id=reference_id
        )

    except Exception as e:
        logger.error(f"Appointment request error: {e}")
        return AppointmentResponse(
            status="error",
            message="We encountered an issue processing your request. Please contact service@aueshah.com directly."
        )


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
