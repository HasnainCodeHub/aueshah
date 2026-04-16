"""T148: FastAPI auth dependencies — extract and verify session JWT from Authorization header."""
import uuid
import logging
from typing import Optional

from fastapi import Depends, Request

from app.auth.session_jwt import decode_session_jwt
from app.models.errors import AuthFailure
from app.db.session import get_session
from app.db.repositories import users as user_repo

logger = logging.getLogger(__name__)


def _extract_bearer(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


async def get_current_user(request: Request, session=Depends(get_session)):
    """Require a valid session JWT. Returns the User DB row. Raises 401 if missing/invalid."""
    token = _extract_bearer(request)
    if not token:
        raise AuthFailure("Authorization header required")

    payload = decode_session_jwt(token)
    user_id = uuid.UUID(payload["sub"])

    if session is None:
        raise AuthFailure("User database unavailable")

    user = await user_repo.get_by_id(session, user_id)
    if user is None:
        raise AuthFailure("User not found")

    return user


async def get_current_user_optional(request: Request, session=Depends(get_session)):
    """Like get_current_user but returns None instead of raising when no token present."""
    token = _extract_bearer(request)
    if not token:
        return None

    try:
        payload = decode_session_jwt(token)
    except AuthFailure:
        return None

    if session is None:
        return None

    user_id = uuid.UUID(payload["sub"])
    return await user_repo.get_by_id(session, user_id)


def require_role(required_role: str):
    """Factory: returns a dependency that checks the user has the required role."""
    async def _check(user=Depends(get_current_user)):
        if user.role != required_role:
            raise AuthFailure("Insufficient permissions")
        return user
    return _check
