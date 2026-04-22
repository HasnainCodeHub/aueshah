"""T190: Appointment repository.

Persists incoming appointment requests collected by the chat concierge.
Mirrors the noor_requests repo style: opaque reference IDs, status transitions,
status-filtered listing for the admin tooling.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Appointment


def _generate_reference_id() -> str:
    """APT-XXXXXXXX (8 hex chars)."""
    return f"APT-{secrets.token_hex(4).upper()}"


async def create(
    session: AsyncSession,
    *,
    email: str,
    appointment_type: str,
    user_id: Optional[uuid.UUID] = None,
    phone: Optional[str] = None,
    preferred_date: Optional[str] = None,
    notes: Optional[str] = None,
) -> Appointment:
    """Insert a new pending appointment request and return it."""
    row = Appointment(
        reference_id=_generate_reference_id(),
        user_id=user_id,
        email=email,
        phone=phone,
        appointment_type=appointment_type,
        preferred_date=preferred_date,
        notes=notes,
        status="pending",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_by_id(session: AsyncSession, appointment_id: uuid.UUID) -> Optional[Appointment]:
    stmt = select(Appointment).where(Appointment.id == appointment_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_by_reference(session: AsyncSession, reference_id: str) -> Optional[Appointment]:
    stmt = select(Appointment).where(Appointment.reference_id == reference_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_for_user(
    session: AsyncSession, user_id: uuid.UUID, limit: int = 20
) -> list[Appointment]:
    stmt = (
        select(Appointment)
        .where(Appointment.user_id == user_id)
        .order_by(Appointment.created_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_by_status(
    session: AsyncSession,
    status: Optional[str] = None,
    limit: int = 50,
) -> list[Appointment]:
    stmt = select(Appointment).order_by(Appointment.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(Appointment.status == status)
    return list((await session.execute(stmt)).scalars().all())


async def update_status(
    session: AsyncSession,
    appointment_id: uuid.UUID,
    *,
    status: str,
    confirmed_by: Optional[str] = None,
    scheduled_at: Optional[datetime] = None,
    meeting_link: Optional[str] = None,
    internal_notes: Optional[str] = None,
) -> Optional[Appointment]:
    """Apply a concierge-side status change."""
    if status not in {"pending", "confirmed", "completed", "cancelled"}:
        raise ValueError(f"Invalid appointment status: {status}")

    values: dict = {
        "status": status,
        "updated_at": datetime.now(timezone.utc),
    }
    if confirmed_by is not None:
        values["confirmed_by"] = confirmed_by
    if scheduled_at is not None:
        values["scheduled_at"] = scheduled_at
    if meeting_link is not None:
        values["meeting_link"] = meeting_link
    if internal_notes is not None:
        values["internal_notes"] = internal_notes

    stmt = update(Appointment).where(Appointment.id == appointment_id).values(**values)
    await session.execute(stmt)
    await session.commit()
    return await get_by_id(session, appointment_id)
