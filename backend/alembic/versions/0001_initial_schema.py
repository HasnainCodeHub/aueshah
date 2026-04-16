"""Initial Phase 2 schema — 5 tables with indexes and triggers.

Revision ID: 0001
Revises:
Create Date: 2026-04-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # updated_at trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 1. users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("wp_user_id", sa.BigInteger, unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("age_range", sa.String(32), nullable=True),
        sa.Column("skin_tone", sa.String(32), nullable=True),
        sa.Column("style_preference", sa.String(64), nullable=True),
        sa.Column("preferred_collection", sa.String(64), nullable=True),
        sa.Column("favorite_metals", ARRAY(sa.Text), server_default="{}"),
        sa.Column("favorite_styles", ARRAY(sa.Text), server_default="{}"),
        sa.Column("role", sa.String(16), nullable=False, server_default="client"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_last_seen_at", "users", ["last_seen_at"])

    # 2. chat_messages
    op.create_table(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("visitor_id", UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("intent", sa.String(32), nullable=True),
        sa.Column("skill", sa.String(32), nullable=True),
        sa.Column("routing_source", sa.String(16), nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("rag_chunk_ids", ARRAY(sa.Text), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system')", name="ck_chat_messages_role"),
    )
    op.create_index("ix_chat_messages_user_created", "chat_messages", ["user_id", sa.text("created_at DESC")])
    op.create_index("ix_chat_messages_visitor_created", "chat_messages", ["visitor_id", sa.text("created_at DESC")])
    op.create_index("ix_chat_messages_session_created", "chat_messages", ["session_id", "created_at"])
    op.create_index("ix_chat_messages_intent", "chat_messages", ["intent"])

    # 3. appointments
    op.create_table(
        "appointments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("reference_id", sa.String(20), unique=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("appointment_type", sa.String(32), nullable=False),
        sa.Column("preferred_date", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("confirmed_by", sa.String(128), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meeting_link", sa.String(512), nullable=True),
        sa.Column("internal_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "appointment_type IN ('virtual', 'in-person', 'bespoke', 'general')",
            name="ck_appointments_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'completed', 'cancelled')",
            name="ck_appointments_status",
        ),
    )
    op.create_index("ix_appointments_user_created", "appointments", ["user_id", sa.text("created_at DESC")])
    op.create_index("ix_appointments_status_created", "appointments", ["status", sa.text("created_at DESC")])

    # 4. noor_allocation_requests
    op.create_table(
        "noor_allocation_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("reference_id", sa.String(20), unique=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("purpose", sa.Text, nullable=False),
        sa.Column("timeline", sa.String(128), nullable=False),
        sa.Column("delivery_location", sa.String(255), nullable=False),
        sa.Column("contact_method", sa.String(16), nullable=False),
        sa.Column("contact_details", sa.String(255), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(128), nullable=True),
        sa.Column("internal_notes", sa.Text, nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="AI Concierge"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("contact_method IN ('email', 'phone', 'both')", name="ck_noor_requests_contact_method"),
        sa.CheckConstraint("status IN ('pending', 'approved', 'declined')", name="ck_noor_requests_status"),
    )
    op.create_index("ix_noor_requests_user_status", "noor_allocation_requests", ["user_id", "status"])
    op.create_index("ix_noor_requests_status_submitted", "noor_allocation_requests", ["status", sa.text("submitted_at DESC")])
    op.create_index("ix_noor_requests_cooldown", "noor_allocation_requests", ["cooldown_until"])

    # 5. user_activity
    op.create_table(
        "user_activity",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("activity_type", sa.String(64), nullable=False),
        sa.Column("details", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_user_activity_user_created", "user_activity", ["user_id", sa.text("created_at DESC")])
    op.create_index("ix_user_activity_type_created", "user_activity", ["activity_type", sa.text("created_at DESC")])

    # updated_at triggers
    for table_name in ("users", "appointments", "noor_allocation_requests"):
        op.execute(f"""
            CREATE TRIGGER {table_name}_set_updated_at
            BEFORE UPDATE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """)


def downgrade() -> None:
    for table_name in ("users", "appointments", "noor_allocation_requests"):
        op.execute(f"DROP TRIGGER IF EXISTS {table_name}_set_updated_at ON {table_name};")

    op.drop_table("user_activity")
    op.drop_table("noor_allocation_requests")
    op.drop_table("appointments")
    op.drop_table("chat_messages")
    op.drop_table("users")

    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")
