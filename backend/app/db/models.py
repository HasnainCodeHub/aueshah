"""SQLAlchemy 2.0 declarative models for Neon Serverless Postgres."""
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wp_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)

    age_range: Mapped[str | None] = mapped_column(String(32), nullable=True)
    skin_tone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    style_preference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preferred_collection: Mapped[str | None] = mapped_column(String(64), nullable=True)
    favorite_metals: Mapped[list | None] = mapped_column(ARRAY(Text), server_default="{}")
    favorite_styles: Mapped[list | None] = mapped_column(ARRAY(Text), server_default="{}")
    profile_facts: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    role: Mapped[str] = mapped_column(String(16), nullable=False, server_default="client")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_users_last_seen_at", "last_seen_at"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    visitor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    skill: Mapped[str | None] = mapped_column(String(32), nullable=True)
    routing_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rag_chunk_ids: Mapped[list | None] = mapped_column(ARRAY(Text), server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="ck_chat_messages_role"),
        Index("ix_chat_messages_user_created", "user_id", created_at.desc()),
        Index("ix_chat_messages_visitor_created", "visitor_id", created_at.desc()),
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
        Index("ix_chat_messages_intent", "intent"),
    )


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    appointment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    preferred_date: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    confirmed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meeting_link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "appointment_type IN ('virtual', 'in-person', 'bespoke', 'general')",
            name="ck_appointments_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'completed', 'cancelled')",
            name="ck_appointments_status",
        ),
        Index("ix_appointments_user_created", "user_id", created_at.desc()),
        Index("ix_appointments_status_created", "status", created_at.desc()),
    )


class NoorAllocationRequest(Base):
    __tablename__ = "noor_allocation_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    timeline: Mapped[str] = mapped_column(String(128), nullable=False)
    delivery_location: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_method: Mapped[str] = mapped_column(String(16), nullable=False)
    contact_details: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, server_default="AI Concierge")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "contact_method IN ('email', 'phone', 'both')",
            name="ck_noor_requests_contact_method",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'declined')",
            name="ck_noor_requests_status",
        ),
        Index("ix_noor_requests_user_status", "user_id", "status"),
        Index("ix_noor_requests_status_submitted", "status", submitted_at.desc()),
        Index("ix_noor_requests_cooldown", "cooldown_until"),
    )


class UserActivity(Base):
    __tablename__ = "user_activity"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_user_activity_user_created", "user_id", created_at.desc()),
        Index("ix_user_activity_type_created", "activity_type", created_at.desc()),
    )
