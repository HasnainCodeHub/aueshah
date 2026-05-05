"""Add users.profile_facts JSONB column.

The column was added in app/db/models.py and is read by the chat
auth + personalization paths, but no migration was committed for it.
On a fresh Neon database (e.g. when migrating to a client-owned account),
queries like SELECT … FROM users blow up with UndefinedColumnError until
this migration runs.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "profile_facts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "profile_facts")
