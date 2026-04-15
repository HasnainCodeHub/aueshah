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


class AppointmentRequest(BaseModel):
    """Request payload for POST /appointment-request endpoint."""
    email: str = Field(..., min_length=5, max_length=255, description="Client email address")
    phone: Optional[str] = Field(None, max_length=20, description="Client phone number (optional)")
    appointment_type: str = Field(..., max_length=100, description="Type: virtual, in-person, bespoke, general")
    preferred_date: Optional[str] = Field(None, max_length=50, description="Preferred date/time (optional)")
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes from client")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email validation."""
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v.lower().strip()


class AppointmentResponse(BaseModel):
    """Response payload for successful appointment request."""
    status: str = Field(default="success", description="success or error")
    message: str = Field(..., description="Confirmation message for client")
    reference_id: Optional[str] = Field(None, description="Unique reference ID for tracking")
