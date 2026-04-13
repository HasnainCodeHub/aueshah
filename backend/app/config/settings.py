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

    # Embedding
    embedding_model: str = "text-embedding-3-small"

    # Timeouts (in seconds)
    chat_timeout_seconds: float = 4.0
    rag_timeout_seconds: float = 0.5
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
