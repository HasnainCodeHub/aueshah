"""Request timeout middleware — 15s hard cap on /chat endpoint."""
import asyncio
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.settings import settings

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = "There appears to be a temporary delay. Please try again shortly."


class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method != "POST" or "/chat" not in request.url.path:
            return await call_next(request)

        try:
            response = await asyncio.wait_for(
                call_next(request),
                timeout=settings.request_timeout_seconds,
            )
            return response
        except asyncio.TimeoutError:
            logger.warning(
                "Request timeout",
                extra={
                    "path": request.url.path,
                    "timeout_seconds": settings.request_timeout_seconds,
                    "ip": request.client.host if request.client else "unknown",
                },
            )
            return JSONResponse(
                status_code=408,
                content={"error": FALLBACK_MESSAGE, "code": 408},
            )
