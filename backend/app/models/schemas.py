"""Pydantic models for request/response validation."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator

MAX_CONTEXT_MESSAGES = 15


def cap_context(messages: Optional[List["ContextMessage"]], max_n: int = MAX_CONTEXT_MESSAGES) -> Optional[List["ContextMessage"]]:
    """Utility: truncate context to the most recent max_n messages."""
    if not messages:
        return messages
    if len(messages) <= max_n:
        return messages
    return messages[-max_n:]


class ContextMessage(BaseModel):
    """A single message in conversation context."""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=10000)


class ChatRequest(BaseModel):
    """Request payload for POST /chat endpoint."""
    message: str = Field(..., min_length=1, max_length=5000)
    context: Optional[List[ContextMessage]] = Field(default=None)
    session_id: Optional[str] = Field(default=None, description="Groups messages into a conversation")

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: Optional[List[ContextMessage]]) -> Optional[List[ContextMessage]]:
        """Hard cap context to MAX_CONTEXT_MESSAGES regardless of what client sends."""
        return cap_context(v)


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


# ─── Phase 2: Auth ────────────────────────────────────────────────

class WPLoginRequest(BaseModel):
    """Exchange a WordPress JWT for our session JWT."""
    wp_token: str = Field(..., min_length=10)
    visitor_id: Optional[str] = Field(None, description="Anonymous visitor cookie to merge")


class AuthResponse(BaseModel):
    """Returned after successful WP login."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: Dict[str, Any]


class UserPublic(BaseModel):
    """Public-facing user profile."""
    id: str
    wp_user_id: int
    email: str
    display_name: str
    age_range: Optional[str] = None
    skin_tone: Optional[str] = None
    style_preference: Optional[str] = None
    preferred_collection: Optional[str] = None
    favorite_metals: Optional[List[str]] = None
    favorite_styles: Optional[List[str]] = None
    role: str = "client"


# ─── Phase 2: Noor Allocation ─────────────────────────────────────

class NoorRequestCreate(BaseModel):
    """Payload for submitting a Noor Collection allocation request."""
    full_name: str = Field(..., min_length=2, max_length=255)
    purpose: str = Field(..., min_length=5, max_length=1000)
    timeline: str = Field(..., max_length=128)
    delivery_location: str = Field(..., max_length=255)
    contact_method: str = Field(..., pattern="^(email|phone|both)$")
    contact_details: str = Field(..., max_length=255)


class NoorRequestResponse(BaseModel):
    """Returned after Noor request creation."""
    status: str = "success"
    message: str
    reference_id: str


class NoorRequestPublic(BaseModel):
    """Client-facing Noor request view."""
    reference_id: str
    full_name: str
    purpose: str
    timeline: str
    delivery_location: str
    contact_method: str
    status: str
    cooldown_until: Optional[str] = None
    submitted_at: str
    reviewed_at: Optional[str] = None


class AdminNoorDecision(BaseModel):
    """Admin payload to approve/decline a Noor request."""
    status: str = Field(..., pattern="^(approved|declined)$")
    internal_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
