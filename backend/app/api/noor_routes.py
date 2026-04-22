"""T181: User-facing Noor allocation routes."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.db.session import get_session
from app.db.repositories import noor_requests as noor_repo
from app.models.errors import DatabaseUnavailable
from app.models.schemas import NoorRequestCreate, NoorRequestPublic, NoorRequestResponse
from app.services.noor_workflow import create_noor_request

logger = logging.getLogger(__name__)

noor_router = APIRouter(prefix="/v1/noor-requests", tags=["noor"])


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


@noor_router.post("", response_model=NoorRequestResponse, status_code=201)
async def submit_noor_request(
    payload: NoorRequestCreate,
    user=Depends(get_current_user),
    session=Depends(get_session),
):
    """Submit a Noor Collection allocation request. Requires authentication.

    Blocks with 409 if the client has a pending request or is still inside the
    cooldown window of a previous approval.
    """
    if session is None:
        raise DatabaseUnavailable()

    row = await create_noor_request(session, user, payload)
    return NoorRequestResponse(
        status="success",
        message=(
            f"Your Noor request ({row.reference_id}) is with our private concierge. "
            f"We will reach out personally within 48 hours."
        ),
        reference_id=row.reference_id,
    )


@noor_router.get("/me", response_model=list[NoorRequestPublic])
async def list_my_noor_requests(
    user=Depends(get_current_user),
    session=Depends(get_session),
):
    """List the authenticated user's Noor allocation requests."""
    if session is None:
        raise DatabaseUnavailable()

    rows = await noor_repo.list_for_user(session, user.id)
    return [_to_public(r) for r in rows]
