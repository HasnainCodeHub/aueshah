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

# 2. CORS — DEV: allow all origins so the WP/Elementor editor can reach localhost.
# ⚠️ PRODUCTION: replace with the locked-down block below before deploying.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",   # wildcard that still permits credentials
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# PRODUCTION CORS (uncomment and remove the block above before deploying):
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "https://aueshah.com",
#         "https://www.aueshah.com",
#     ],
#     allow_credentials=True,
#     allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
#     allow_headers=["*"],
# )

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
