"""T182: Admin-only routes for Noor allocation review.

Gated by a static `X-Admin-Token` header compared against `ADMIN_API_TOKEN`.
This is intentionally a shared-secret rather than per-user role since the
admin surface is a small concierge team using internal tooling, not WP users.
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.config.settings import settings
from app.db.repositories import noor_requests as noor_repo
from app.db.repositories import users as user_repo
from app.db.session import get_session
from app.models.errors import AuthFailure, DatabaseUnavailable, ValidationError
from app.models.schemas import AdminNoorDecision, NoorRequestPublic, PIIDeletionResponse
from app.services.noor_workflow import review_noor_request

logger = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/v1/admin", tags=["admin"])


async def require_admin_token(x_admin_token: Optional[str] = Header(default=None)) -> None:
    """Reject requests missing or mismatching the admin shared secret."""
    expected = settings.admin_api_token
    if not expected:
        raise AuthFailure("Admin endpoints disabled — ADMIN_API_TOKEN not configured")
    if not x_admin_token or x_admin_token != expected:
        raise AuthFailure("Invalid admin token")


def _to_public(row) -> NoorRequestPublic:
    return NoorRequestPublic(
        reference_id=row.reference_id,
        full_name=row.full_name,
        purpose=row.purpose,
        timeline=row.timeline,
        delivery_location=row.delivery_location,
        contact_method=row.contact_method,
        status=row.status,
        cooldown_until=row.cooldown_until.isoformat() if row.cooldown_until else None,
        submitted_at=row.submitted_at.isoformat() if row.submitted_at else "",
        reviewed_at=row.reviewed_at.isoformat() if row.reviewed_at else None,
    )


@admin_router.get(
    "/noor-requests",
    response_model=list[NoorRequestPublic],
    dependencies=[Depends(require_admin_token)],
)
async def list_noor_requests(
    status: Optional[str] = Query(default=None, pattern="^(pending|approved|declined)$"),
    limit: int = Query(default=50, ge=1, le=200),
    session=Depends(get_session),
):
    """List Noor requests, optionally filtered by status."""
    if session is None:
        raise DatabaseUnavailable()
    rows = await noor_repo.list_by_status(session, status=status, limit=limit)
    return [_to_public(r) for r in rows]


@admin_router.get(
    "/noor-requests/{request_id}",
    response_model=NoorRequestPublic,
    dependencies=[Depends(require_admin_token)],
)
async def get_noor_request(request_id: uuid.UUID, session=Depends(get_session)):
    if session is None:
        raise DatabaseUnavailable()
    row = await noor_repo.get_by_id(session, request_id)
    if row is None:
        raise ValidationError(f"Noor request {request_id} not found")
    return _to_public(row)


@admin_router.get("/metrics", dependencies=[Depends(require_admin_token)])
async def metrics_endpoint() -> Response:
    """Prometheus scrape endpoint. Gated by the same shared-secret as the
    admin tooling so it's not publicly exposed even when the app is."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@admin_router.patch(
    "/noor-requests/{request_id}",
    response_model=NoorRequestPublic,
    dependencies=[Depends(require_admin_token)],
)
async def review_noor(
    request_id: uuid.UUID,
    payload: AdminNoorDecision,
    session=Depends(get_session),
):
    """Approve or decline a pending Noor request and notify the client."""
    if session is None:
        raise DatabaseUnavailable()

    async def _user_lookup(user_id):
        return await user_repo.get_by_id(session, user_id)

    row = await review_noor_request(
        session,
        request_id,
        decision=payload.status,
        user_lookup=_user_lookup,
        reviewed_by=payload.reviewed_by,
        internal_notes=payload.internal_notes,
    )
    if row is None:
        raise ValidationError(f"Noor request {request_id} not found")
    return _to_public(row)


@admin_router.delete(
    "/users/{user_id}",
    response_model=PIIDeletionResponse,
    dependencies=[Depends(require_admin_token)],
)
async def delete_user_pii(user_id: uuid.UUID, session=Depends(get_session)):
    """T204: GDPR right-to-erasure.

    Hard-deletes all PII for the given user across chat_messages, appointments,
    noor_allocation_requests, user_activity, and users. Anonymous visitor
    messages (user_id IS NULL) are not affected.
    """
    if session is None:
        raise DatabaseUnavailable()
    result = await user_repo.delete_user_pii(session, user_id)
    if not result["deleted"]:
        logger.info("PII deletion requested for missing user", extra={"user_id": str(user_id)})
        return PIIDeletionResponse(
            deleted=False,
            user_id=str(user_id),
            reason=result.get("reason", "user_not_found"),
        )
    logger.warning(
        "PII deletion completed",
        extra={"user_id": str(user_id), "counts": result["counts"]},
    )
    return PIIDeletionResponse(
        deleted=True,
        user_id=str(user_id),
        counts=result["counts"],
    )
