"""Application settings and configuration."""
import os
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4.1"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "aueshah_knowledge"

    # Embedding
    embedding_model: str = "text-embedding-3-large"
    embedding_dim: int = 3072

    # Timeouts (in seconds)
    chat_timeout_seconds: float = 4.0
    rag_timeout_seconds: float = 2.5
    routing_timeout_ms: int = 200

    # Logging
    log_level: str = "INFO"

    # Feature flags
    enable_rag: bool = True
    enable_retry: bool = True
    max_retries: int = 2

    # Phase 2: Neon Postgres
    neon_database_url: str = ""

    # Phase 2: Redis
    redis_url: str = ""

    # Phase 2: Rate limiting & timeout
    # Rate limiting is always on when REDIS_URL is configured; absent REDIS_URL
    # the limiter fails open (see app/middleware/rate_limiter.py).
    rate_limit_per_min: int = 5
    request_timeout_seconds: int = 15
    max_context_messages: int = 15

    # Phase 2: WordPress Auth (HS256 via JWT Authentication for WP-API plugin)
    wp_base_url: str = ""
    wp_issuer: str = ""
    wp_jwt_secret: str = Field(default="", validation_alias="JWT_AUTH_SECRET_KEY")

    # Phase 2: Session JWT
    jwt_signing_key: str = ""
    jwt_expires_seconds: int = 86400

    # Phase 2: Admin
    admin_api_token: str = ""

    # Phase 2: Resend (email)
    resend_api_key: str = ""
    # Until aueshah.com is verified in Resend, use the sandbox sender
    # `onboarding@resend.dev`. Swap to a verified address when ready.
    resend_from_email: str = "Aueshah Concierge <onboarding@resend.dev>"
    # Comma-separated for multiple inboxes — workflows fan out one Resend send
    # per recipient. Sandbox-only Resend accounts will silently 403 on any
    # address except the registered one until a domain is verified.
    concierge_alert_email: str = "shahs.jewel@gmail.com,service@aueshah.com"

    @property
    def concierge_alert_recipients(self) -> list[str]:
        """Split concierge_alert_email on commas; trim; drop empties."""
        return [e.strip() for e in self.concierge_alert_email.split(",") if e.strip()]

    # Phase 2: Business logic
    noor_cooldown_days: int = 365
    noor_max_allocations: int = 143

    # CORS — comma-separated allowlist. Defaults locked to production hostnames;
    # override in .env for local dev (e.g. add http://localhost:3000 for the
    # Next.js test harness or http://localhost:8001 for direct probes).
    cors_allowed_origins: str = "https://aueshah.com,https://www.aueshah.com"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Export the OpenAI key to the process environment so SDKs that read it directly
# (e.g. the openai-agents runtime) can find it without us threading the key through.
if settings.openai_api_key:
    os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
