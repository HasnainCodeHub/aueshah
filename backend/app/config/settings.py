"""Application settings and configuration."""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4-turbo-preview"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "aueshah_knowledge"

    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

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

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Export the OpenAI key to the process environment so SDKs that read it directly
# (e.g. the openai-agents runtime) can find it without us threading the key through.
if settings.openai_api_key:
    os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
