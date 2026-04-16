"""T133: Anonymous visitor_id cookie — issued on first contact, merged on login."""
import uuid
import hmac
import hashlib
import logging

from fastapi import Request, Response

from app.config.settings import settings

logger = logging.getLogger(__name__)

COOKIE_NAME = "aueshah_visitor_id"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year


def _sign(visitor_id: str) -> str:
    key = (settings.jwt_signing_key or "dev-fallback-key").encode()
    sig = hmac.new(key, visitor_id.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{visitor_id}.{sig}"


def _verify(signed: str) -> str | None:
    if "." not in signed:
        return None
    vid, sig = signed.rsplit(".", 1)
    expected = _sign(vid)
    if hmac.compare_digest(expected, signed):
        return vid
    return None


def get_visitor_id(request: Request) -> str:
    """Extract visitor_id from cookie, or generate a new one."""
    cookie = request.cookies.get(COOKIE_NAME)
    if cookie:
        vid = _verify(cookie)
        if vid:
            return vid
        logger.warning("Invalid visitor cookie — issuing new one")
    return str(uuid.uuid4())


def set_visitor_cookie(response: Response, visitor_id: str) -> None:
    """Set signed visitor_id cookie on the response."""
    signed = _sign(visitor_id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=signed,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,  # Set True in production behind HTTPS
    )
