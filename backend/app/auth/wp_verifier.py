"""T145: Verify WordPress-issued JWTs via cached JWKS (RS256)."""
import time
import logging
from typing import Any

import httpx
from jose import jwt, JWTError, jwk

from app.config.settings import settings
from app.models.errors import AuthFailure

logger = logging.getLogger(__name__)

_jwks_cache: dict[str, Any] = {}
_jwks_fetched_at: float = 0


async def _fetch_jwks() -> dict[str, Any]:
    """Fetch JWKS from WP endpoint. Cache in-memory for TTL seconds."""
    global _jwks_cache, _jwks_fetched_at

    now = time.time()
    if _jwks_cache and (now - _jwks_fetched_at) < settings.wp_jwks_cache_ttl:
        return _jwks_cache

    if not settings.wp_jwks_url:
        raise AuthFailure("WordPress JWKS URL not configured")

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(settings.wp_jwks_url)
            resp.raise_for_status()
            data = resp.json()

        keys_by_kid = {}
        for key_data in data.get("keys", []):
            kid = key_data.get("kid", "default")
            keys_by_kid[kid] = key_data

        if not keys_by_kid:
            raise AuthFailure("JWKS response contained no keys")

        _jwks_cache = keys_by_kid
        _jwks_fetched_at = now
        logger.info("JWKS refreshed", extra={"key_count": len(keys_by_kid)})
        return keys_by_kid

    except AuthFailure:
        raise
    except Exception as e:
        logger.error("Failed to fetch JWKS", exc_info=True)
        if _jwks_cache:
            logger.warning("Using stale JWKS cache after fetch failure")
            return _jwks_cache
        raise AuthFailure("Unable to verify identity — please try again later")


class WPClaims:
    """Parsed claims from a verified WP JWT."""
    def __init__(self, sub: int, email: str, display_name: str, raw: dict):
        self.wp_user_id = sub
        self.email = email
        self.display_name = display_name
        self.raw = raw


async def verify_wp_token(token: str) -> WPClaims:
    """Verify a WP-issued JWT and return parsed claims. Raises AuthFailure on any problem."""
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        raise AuthFailure("Malformed token")

    kid = unverified_header.get("kid", "default")
    keys = await _fetch_jwks()
    key_data = keys.get(kid)

    if not key_data:
        _jwks_cache.clear()
        keys = await _fetch_jwks()
        key_data = keys.get(kid)
        if not key_data:
            raise AuthFailure("Unknown signing key")

    try:
        public_key = jwk.construct(key_data)
    except Exception:
        raise AuthFailure("Invalid key format in JWKS")

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
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

    sub = payload.get("sub") or payload.get("data", {}).get("user", {}).get("id")
    email = payload.get("email") or payload.get("data", {}).get("user", {}).get("email", "")
    display_name = (
        payload.get("display_name")
        or payload.get("data", {}).get("user", {}).get("display_name", "")
        or email.split("@")[0]
    )

    if not sub:
        raise AuthFailure("Token missing user ID")

    return WPClaims(sub=int(sub), email=str(email), display_name=str(display_name), raw=payload)


def clear_jwks_cache():
    """For testing — force JWKS refetch on next call."""
    global _jwks_cache, _jwks_fetched_at
    _jwks_cache = {}
    _jwks_fetched_at = 0
