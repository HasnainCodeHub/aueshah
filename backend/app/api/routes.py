"""FastAPI routes for the chat API."""
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.models.schemas import ChatRequest, ChatResponse, ErrorResponse
from app.models.errors import ValidationError, InjectionDetected
from app.utils.validators import sanitize_input, detect_prompt_injection, validate_context
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

        # Step 3: Validate context
        context = validate_context(request.context)

        # Step 4: Create validated request
        validated_request = ChatRequest(message=message, context=context)

        # Step 5: Orchestrate request
        response = await orchestrator.handle_chat(validated_request)

        return response

    except ValidationError as e:
        logger.warning(f"Validation error: {e.message}")
        return JSONResponse(status_code=400, content=ErrorResponse(error=e.message, code=400).model_dump())

    except InjectionDetected as e:
        logger.warning(f"Injection detected: {e.message}")
        return JSONResponse(status_code=400, content=ErrorResponse(error=e.message, code=400).model_dump())

    except Exception as e:
        reply, code = FailureHandler.handle_exception(e)
        return JSONResponse(status_code=code, content=ErrorResponse(error=reply, code=code).model_dump())


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
