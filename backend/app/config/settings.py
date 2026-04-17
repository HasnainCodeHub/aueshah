"""Application settings and configuration."""
import os
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
    rate_limit_per_min: int = 5
    request_timeout_seconds: int = 15
    enable_rate_limit: bool = False
    max_context_messages: int = 15

    # Phase 2: WordPress Auth
    wp_base_url: str = ""
    wp_jwks_url: str = ""
    wp_issuer: str = ""
    wp_jwks_cache_ttl: int = 600

    # Phase 2: Session JWT
    jwt_signing_key: str = ""
    jwt_expires_seconds: int = 86400

    # Phase 2: Admin
    admin_api_token: str = ""

    # Phase 2: SendGrid
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = "concierge@aueshah.com"
    sendgrid_from_name: str = "Aueshah Concierge"
    concierge_alert_email: str = "concierge@aueshah.com"

    # Phase 2: Slack
    slack_webhook_noor: str = ""
    slack_webhook_appointments: str = ""

    # Phase 2: Business logic
    noor_cooldown_days: int = 365
    noor_max_allocations: int = 143

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Export the OpenAI key to the process environment so SDKs that read it directly
# (e.g. the openai-agents runtime) can find it without us threading the key through.
if settings.openai_api_key:
    os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
