"""Unified error envelope middleware — all non-2xx responses follow {error, code, retry_after?}."""
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.models.errors import ChatException, RateLimited

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = "There appears to be a temporary delay. Please try again shortly."


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except RateLimited as e:
            logger.warning("Rate limit exceeded", extra={"path": request.url.path, "ip": request.client.host})
            return JSONResponse(
                status_code=429,
                content={"error": FALLBACK_MESSAGE, "code": 429, "retry_after": 60},
                headers={"Retry-After": "60"},
            )
        except ChatException as e:
            logger.warning(f"Chat exception: {e.message}", extra={"code": e.code, "path": request.url.path})
            safe_message = e.message if e.code < 500 else FALLBACK_MESSAGE
            return JSONResponse(
                status_code=e.code,
                content={"error": safe_message, "code": e.code},
            )
        except Exception:
            logger.exception("Unhandled exception", extra={"path": request.url.path})
            return JSONResponse(
                status_code=500,
                content={"error": FALLBACK_MESSAGE, "code": 500},
            )
