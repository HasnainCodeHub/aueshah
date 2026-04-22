"""T207: Request-context middleware — assigns a request_id and exposes it.

Reads `X-Request-ID` from the incoming request if present (so trace IDs from
upstream proxies survive), otherwise mints a fresh one. The id is propagated
back via the `X-Request-ID` response header so clients/log aggregators can
correlate.
"""
from __future__ import annotations

import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logging import reset_request_context, set_request_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        tokens = set_request_context(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            reset_request_context(tokens)
        response.headers["X-Request-ID"] = request_id
        return response
