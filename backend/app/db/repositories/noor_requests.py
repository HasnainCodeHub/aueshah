"""T177: Noor allocation request repository.

The data model carries two independent block conditions:
  - `status='pending'` rows are an active in-flight request.
  - `status='approved'` rows with `cooldown_until > now()` are still in the
    post-allocation cooldown window.

`user_has_active()` returns True if either condition holds, and is what the
workflow consults before accepting a new submission.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import NoorAllocationRequest


def _generate_reference_id() -> str:
    """NOR-XXXXXXXX (8 hex chars) — collision-resistant enough at our scale."""
    return f"NOR-{secrets.token_hex(4).upper()}"


async def create(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    full_name: str,
    purpose: str,
    timeline: str,
    delivery_location: str,
    contact_method: str,
    contact_details: str,
) -> NoorAllocationRequest:
    """Insert a new pending Noor allocation request and return it."""
    row = NoorAllocationRequest(
        reference_id=_generate_reference_id(),
        user_id=user_id,
        full_name=full_name,
        purpose=purpose,
        timeline=timeline,
        delivery_location=delivery_location,
        contact_method=contact_method,
        contact_details=contact_details,
        status="pending",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def user_has_active(session: AsyncSession, user_id: uuid.UUID) -> Optional[NoorAllocationRequest]:
    """Return the blocking row if the user has either a pending request OR an
    approved request still inside its cooldown window. Otherwise None."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(NoorAllocationRequest)
        .where(NoorAllocationRequest.user_id == user_id)
        .where(
            (NoorAllocationRequest.status == "pending")
            | (
                (NoorAllocationRequest.status.in_(["approved", "declined"]))
                & (NoorAllocationRequest.cooldown_until > now)
            )
        )
        .order_by(NoorAllocationRequest.submitted_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def count_approved(session: AsyncSession) -> int:
    """Return the total number of approved Noor allocation requests."""
    stmt = select(func.count()).select_from(NoorAllocationRequest).where(
        NoorAllocationRequest.status == "approved"
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def get_by_id(session: AsyncSession, request_id: uuid.UUID) -> Optional[NoorAllocationRequest]:
    stmt = select(NoorAllocationRequest).where(NoorAllocationRequest.id == request_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_by_reference(session: AsyncSession, reference_id: str) -> Optional[NoorAllocationRequest]:
    stmt = select(NoorAllocationRequest).where(NoorAllocationRequest.reference_id == reference_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_for_user(session: AsyncSession, user_id: uuid.UUID, limit: int = 20) -> list[NoorAllocationRequest]:
    stmt = (
        select(NoorAllocationRequest)
        .where(NoorAllocationRequest.user_id == user_id)
        .order_by(NoorAllocationRequest.submitted_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_by_status(
    session: AsyncSession,
    status: Optional[str] = None,
    limit: int = 50,
) -> list[NoorAllocationRequest]:
    stmt = select(NoorAllocationRequest).order_by(NoorAllocationRequest.submitted_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(NoorAllocationRequest.status == status)
    return list((await session.execute(stmt)).scalars().all())


async def review(
    session: AsyncSession,
    request_id: uuid.UUID,
    *,
    status: str,
    cooldown_days: int,
    reviewed_by: Optional[str] = None,
    internal_notes: Optional[str] = None,
) -> Optional[NoorAllocationRequest]:
    """Apply an admin decision. Approval sets cooldown_until to now+cooldown_days;
    decline leaves cooldown null (the user may submit again immediately)."""
    if status not in {"approved", "declined"}:
        raise ValueError(f"Invalid review status: {status}")

    now = datetime.now(timezone.utc)
    values: dict = {
        "status": status,
        "reviewed_at": now,
        "reviewed_by": reviewed_by,
        "internal_notes": internal_notes,
        "updated_at": now,
        "cooldown_until": now + timedelta(days=cooldown_days),
    }

    stmt = update(NoorAllocationRequest).where(NoorAllocationRequest.id == request_id).values(**values)
    await session.execute(stmt)
    await session.commit()
    return await get_by_id(session, request_id)
