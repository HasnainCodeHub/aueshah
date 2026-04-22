"""Verify WordPress-issued HS256 JWTs from the JWT Authentication for WP-API plugin."""
import logging
from typing import Any

import httpx
from jose import jwt, JWTError

from app.config.settings import settings
from app.models.errors import AuthFailure

logger = logging.getLogger(__name__)


class WPClaims:
    """Parsed claims from a verified WP JWT."""
    def __init__(self, sub: int, email: str, display_name: str, raw: dict):
        self.wp_user_id = sub
        self.email = email
        self.display_name = display_name
        self.raw = raw


async def _hydrate_from_users_me(token: str) -> dict[str, Any]:
    """Call GET /wp-json/wp/v2/users/me to fill in fields absent from the JWT claims."""
    if not settings.wp_base_url:
        return {}
    url = f"{settings.wp_base_url.rstrip('/')}/wp-json/wp/v2/users/me"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code != 200:
                logger.warning(
                    "WP /users/me returned non-200",
                    extra={"status": resp.status_code},
                )
                return {}
            body = resp.json()
            return body if isinstance(body, dict) else {}
    except Exception:
        logger.warning("Failed to hydrate WP user details from /users/me", exc_info=True)
        return {}


async def verify_wp_token(token: str) -> WPClaims:
    """Verify a WP-issued HS256 JWT and return parsed claims.

    Raises AuthFailure on any problem (bad signature, expired, wrong issuer, etc).
    """
    if not settings.wp_jwt_secret:
        raise AuthFailure("WordPress JWT secret not configured")

    try:
        jwt.get_unverified_header(token)
    except JWTError:
        raise AuthFailure("Malformed token")

    try:
        payload = jwt.decode(
            token,
            settings.wp_jwt_secret,
            algorithms=["HS256"],
            options={
                "verify_aud": False,
                "verify_sub": False,
                "leeway": 30,
            },
        )
    except jwt.ExpiredSignatureError:
        raise AuthFailure("Token expired")
    except JWTError as e:
        raise AuthFailure(f"Token verification failed: {e}")

    if settings.wp_issuer and payload.get("iss") != settings.wp_issuer:
        raise AuthFailure("Invalid token issuer")

    # Chávez-style plugin nests user id under data.user.id
    sub = payload.get("sub") or payload.get("data", {}).get("user", {}).get("id")
    if not sub:
        raise AuthFailure("Token missing user ID")

    email = payload.get("email") or payload.get("data", {}).get("user", {}).get("email", "")
    display_name = (
        payload.get("display_name")
        or payload.get("data", {}).get("user", {}).get("display_name", "")
    )

    if not email or not display_name:
        details = await _hydrate_from_users_me(token)
        if details:
            email = email or details.get("email") or ""
            display_name = (
                display_name
                or details.get("name")
                or details.get("slug")
                or ""
            )

    if not email:
        email = f"wp_user_{sub}@aueshah.local"
        logger.warning(
            "WP token had no email and /users/me couldn't hydrate one",
            extra={"wp_user_id": sub},
        )
    if not display_name:
        display_name = email.split("@")[0] if "@" in email else f"user_{sub}"

    return WPClaims(
        sub=int(sub),
        email=str(email),
        display_name=str(display_name),
        raw=payload,
    )
