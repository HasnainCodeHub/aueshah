"""Pydantic models for request/response validation."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class ContextMessage(BaseModel):
    """A single message in conversation context."""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=10000)


class ChatRequest(BaseModel):
    """Request payload for POST /chat endpoint."""
    message: str = Field(..., min_length=1, max_length=5000)
    context: Optional[List[ContextMessage]] = Field(default=None, max_length=15)

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: Optional[List[ContextMessage]]) -> Optional[List[ContextMessage]]:
        """Ensure context is ordered chronologically and well-formed."""
        if v is None:
            return v
        if len(v) > 15:
            # Truncate to last 15 messages
            return v[-15:]
        return v


class ChatResponse(BaseModel):
    """Response payload for successful /chat request."""
    reply: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata: intent, skill, latency_ms, routing_source"
    )


class ErrorResponse(BaseModel):
    """Response payload for error cases."""
    error: str = Field(..., min_length=1)
    code: int = Field(..., ge=400, le=599)


class RAGChunk(BaseModel):
    """A retrieved knowledge chunk from vector store."""
    content: str
    source: Optional[str] = None
    relevance_score: float = Field(ge=0.0, le=1.0)
