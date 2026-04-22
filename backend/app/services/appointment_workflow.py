"""T192: Appointment workflow — orchestrates DB writes + notifications.

Sits between routes and the appointments repository. Mirrors noor_workflow:
  - Insert the row.
  - Fire SendGrid notifications fire-and-forget so the request path
    doesn't pay for them.
  - Optionally log a user_activity row when the requester is authenticated.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.models import Appointment
from app.db.repositories import appointments as appt_repo
from app.services.notifications import email as email_notifier
from app.services.persistence_writer import log_activity

logger = logging.getLogger(__name__)


async def _fire_notifications(row: Appointment, *, user_id: Optional[uuid.UUID]) -> None:
    """Run notifications (and activity log if authed) without holding the request open."""
    coros = [
        email_notifier.send_client_appointment_confirmation(
            to_email=row.email,
            reference_id=row.reference_id,
            appointment_type=row.appointment_type,
            preferred_date=row.preferred_date,
        ),
        email_notifier.send_concierge_appointment_alert(
            to_email=settings.concierge_alert_email,
            reference_id=row.reference_id,
            client_email=row.email,
            appointment_type=row.appointment_type,
            phone=row.phone,
            preferred_date=row.preferred_date,
            notes=row.notes,
        ),
    ]
    if user_id is not None:
        coros.append(
            log_activity(
                user_id=user_id,
                activity_type="appointment_requested",
                details={
                    "reference_id": row.reference_id,
                    "appointment_type": row.appointment_type,
                },
            )
        )
    await asyncio.gather(*coros, return_exceptions=True)


async def create_appointment(
    session: AsyncSession,
    *,
    email: str,
    appointment_type: str,
    user_id: Optional[uuid.UUID] = None,
    phone: Optional[str] = None,
    preferred_date: Optional[str] = None,
    notes: Optional[str] = None,
) -> Appointment:
    """Insert an appointment row and schedule notifications."""
    row = await appt_repo.create(
        session,
        email=email,
        appointment_type=appointment_type,
        user_id=user_id,
        phone=phone,
        preferred_date=preferred_date,
        notes=notes,
    )

    asyncio.create_task(_fire_notifications(row, user_id=user_id))
    logger.info(
        "Appointment created",
        extra={
            "reference_id": row.reference_id,
            "appointment_type": appointment_type,
            "user_id": str(user_id) if user_id else None,
        },
    )
    return row
