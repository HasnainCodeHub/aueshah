"""FastAPI application entry point."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.utils.logging import setup_logging
from app.config.settings import settings
from app.api.routes import router
from app.api.auth_routes import auth_router
from app.api.noor_routes import noor_router
from app.api.admin_routes import admin_router
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.timeout import TimeoutMiddleware
from app.middleware.rate_limiter import close_redis
from app.db.session import close_engine

# Setup logging
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Concierge Backend",
    description="Stateless chat API with skill routing, RAG integration, and Phase 2 persistence",
    version="2.0.0",
)

# Middleware stack (order matters: outermost runs first)
# 1. Error handler — catches all unhandled exceptions, returns safe JSON envelope
app.add_middleware(ErrorHandlerMiddleware)

# 1a. Request context — must run inside the error handler so the request_id
# is also stamped on logs emitted by the error path.
app.add_middleware(RequestContextMiddleware)

# 2. CORS — locked to the allowlist in settings.cors_origins. Default
# allowlist is production-only (aueshah.com / www.aueshah.com); local dev
# overrides via CORS_ALLOWED_ORIGINS in .env. allow_credentials=True is
# required for the WP-bridged Bearer auth flow.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Chrome "Private Network Access" — public HTTPS sites calling http://127.0.0.1
# require this header on the preflight. Tightened: only echo the origin back
# when it's in the CORS allowlist, otherwise the PNA path would silently
# bypass the lockdown by reflecting any caller's origin.
@app.middleware("http")
async def private_network_access(request, call_next):
    origin = request.headers.get("origin", "")
    if request.method == "OPTIONS" and request.headers.get("access-control-request-private-network", "").lower() == "true":
        from fastapi.responses import Response
        if origin in settings.cors_origins:
            return Response(
                status_code=204,
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": request.headers.get("access-control-request-headers", "*"),
                    "Access-Control-Allow-Private-Network": "true",
                    "Access-Control-Max-Age": "86400",
                },
            )
        return Response(status_code=403)
    response = await call_next(request)
    if origin in settings.cors_origins:
        response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response

# 3. Timeout — 15s hard cap on /chat requests
app.add_middleware(TimeoutMiddleware)

# Include routes
app.include_router(router)
app.include_router(auth_router)
app.include_router(noor_router)
app.include_router(admin_router)


@app.on_event("startup")
async def startup():
    """Log startup."""
    logger.info("Application started", extra={"component": "main", "version": "2.0.0"})


@app.on_event("shutdown")
async def shutdown():
    """Clean up connections and log shutdown."""
    await close_redis()
    await close_engine()
    logger.info("Application shutting down", extra={"component": "main"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level=settings.log_level.lower())
