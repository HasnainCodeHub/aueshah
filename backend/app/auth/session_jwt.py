"""T146: Mint and decode our HS256 session JWTs."""
import time
import uuid
import logging
from typing import Any

from jose import jwt, JWTError

from app.config.settings import settings
from app.models.errors import AuthFailure

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"


def _get_signing_key() -> str:
    if not settings.jwt_signing_key:
        raise AuthFailure("JWT signing key not configured")
    return settings.jwt_signing_key


def mint_session_jwt(
    user_id: uuid.UUID,
    wp_user_id: int,
    role: str = "client",
) -> tuple[str, int]:
    """Create an HS256 session token. Returns (token, expires_in_seconds)."""
    now = int(time.time())
    expires_in = settings.jwt_expires_seconds
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "wp_uid": wp_user_id,
        "role": role,
        "iat": now,
        "exp": now + expires_in,
    }
    token = jwt.encode(payload, _get_signing_key(), algorithm=ALGORITHM)
    return token, expires_in


def decode_session_jwt(token: str) -> dict[str, Any]:
    """Decode and verify a session JWT. Raises AuthFailure on any problem."""
    try:
        payload = jwt.decode(
            token,
            _get_signing_key(),
            algorithms=[ALGORITHM],
            options={"leeway": 30},
        )
    except jwt.ExpiredSignatureError:
        raise AuthFailure("Session expired — please log in again")
    except JWTError:
        raise AuthFailure("Invalid session token")

    if not payload.get("sub"):
        raise AuthFailure("Token missing user ID")

    return payload
