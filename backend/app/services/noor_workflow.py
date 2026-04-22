"""T180: Noor allocation workflow — orchestrates DB writes + notifications.

Lives between routes and the noor_requests repository. Responsible for:
  - Cooldown / pending-conflict enforcement on submission.
  - Reference-ID generation (handled in repo).
  - Firing email notifications without blocking the request path.
  - Logging activity rows on the user_activity stream.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.models import NoorAllocationRequest, User
from app.db.repositories import noor_requests as noor_repo
from app.models.errors import CooldownActive, NoorPendingConflict
from app.models.schemas import NoorRequestCreate
from app.services.notifications import email as email_notifier
from app.services.persistence_writer import log_activity
from app.utils.metrics import NOOR_REQUESTS_TOTAL

logger = logging.getLogger(__name__)


async def _fire_notifications_on_create(row: NoorAllocationRequest, user: User) -> None:
    """Run notifications + activity log without holding the request path open."""
    await asyncio.gather(
        email_notifier.send_client_noor_confirmation(
            to_email=user.email,
            full_name=row.full_name,
            reference_id=row.reference_id,
        ),
        email_notifier.send_concierge_noor_alert(
            to_email=settings.concierge_alert_email,
            reference_id=row.reference_id,
            full_name=row.full_name,
            purpose=row.purpose,
            timeline=row.timeline,
            contact_method=row.contact_method,
            contact_details=row.contact_details,
        ),
        log_activity(
            user_id=user.id,
            activity_type="noor_request_submitted",
            details={"reference_id": row.reference_id, "timeline": row.timeline},
        ),
        return_exceptions=True,
    )


async def _fire_notifications_on_review(row: NoorAllocationRequest, user: User) -> None:
    await asyncio.gather(
        email_notifier.send_client_noor_decision(
            to_email=user.email,
            full_name=row.full_name,
            reference_id=row.reference_id,
            decision=row.status,
        ),
        log_activity(
            user_id=user.id,
            activity_type=f"noor_request_{row.status}",
            details={"reference_id": row.reference_id, "reviewed_by": row.reviewed_by},
        ),
        return_exceptions=True,
    )


async def create_noor_request(
    session: AsyncSession,
    user: User,
    payload: NoorRequestCreate,
) -> NoorAllocationRequest:
    """Validate eligibility, insert the request, schedule notifications. Raises
    NoorPendingConflict / CooldownActive on block."""
    blocking = await noor_repo.user_has_active(session, user.id)
    if blocking is not None:
        if blocking.status == "pending":
            NOOR_REQUESTS_TOTAL.labels(outcome="blocked_pending").inc()
            raise NoorPendingConflict()
        NOOR_REQUESTS_TOTAL.labels(outcome="blocked_cooldown").inc()
        raise CooldownActive()

    row = await noor_repo.create(
        session,
        user_id=user.id,
        full_name=payload.full_name,
        purpose=payload.purpose,
        timeline=payload.timeline,
        delivery_location=payload.delivery_location,
        contact_method=payload.contact_method,
        contact_details=payload.contact_details,
    )

    NOOR_REQUESTS_TOTAL.labels(outcome="created").inc()
    asyncio.create_task(_fire_notifications_on_create(row, user))
    logger.info(
        "Noor request created",
        extra={"reference_id": row.reference_id, "user_id": str(user.id)},
    )
    return row


async def review_noor_request(
    session: AsyncSession,
    request_id: uuid.UUID,
    *,
    decision: str,
    user_lookup,
    reviewed_by: Optional[str] = None,
    internal_notes: Optional[str] = None,
) -> Optional[NoorAllocationRequest]:
    """Apply admin decision and notify the client. `user_lookup` is an awaitable
    callable resolving the request's owning User (kept as a callback so this
    module doesn't depend on the users repo directly)."""
    row = await noor_repo.review(
        session,
        request_id,
        status=decision,
        cooldown_days=settings.noor_cooldown_days,
        reviewed_by=reviewed_by,
        internal_notes=internal_notes,
    )
    if row is None:
        return None

    user = await user_lookup(row.user_id)
    if user is not None:
        asyncio.create_task(_fire_notifications_on_review(row, user))
    logger.info(
        "Noor request reviewed",
        extra={"reference_id": row.reference_id, "decision": decision},
    )
    return row
