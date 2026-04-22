"""T149: Auth routes — WP login exchange, /me profile, logout."""
import uuid
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.models.schemas import WPLoginRequest, AuthResponse, UserPublic
from app.models.errors import AuthFailure, DatabaseUnavailable
from app.auth.wp_verifier import verify_wp_token
from app.auth.session_jwt import mint_session_jwt
from app.auth.visitor import get_visitor_id
from app.auth.dependencies import get_current_user
from app.db.session import get_session
from app.db.repositories import users as user_repo
from app.db.repositories import chat_history as chat_repo

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/v1/auth", tags=["auth"])


@auth_router.post("/wp-login", response_model=AuthResponse)
async def wp_login(body: WPLoginRequest, http_request: Request, session=Depends(get_session)):
    """Exchange a WordPress JWT for our session JWT. Merges anonymous chat history."""
    if session is None:
        raise DatabaseUnavailable("User database unavailable — login requires database")

    wp_claims = await verify_wp_token(body.wp_token)

    # Prefer body-supplied fields (from WP /token response) over verifier fallbacks,
    # since WP REST API hides real email from /wp/v2/users/me in default context.
    real_email = body.user_email or wp_claims.email
    real_display_name = body.user_display_name or wp_claims.display_name

    user = await user_repo.upsert_from_wp_claims(
        session,
        wp_user_id=wp_claims.wp_user_id,
        email=real_email,
        display_name=real_display_name,
    )

    # T150: Merge anonymous visitor history to authenticated user
    visitor_id_str = body.visitor_id or get_visitor_id(http_request)
    try:
        vid = uuid.UUID(visitor_id_str)
        merged = await chat_repo.merge_visitor_to_user(session, vid, user.id)
        if merged:
            logger.info("Merged anonymous history", extra={"count": merged, "user_id": str(user.id)})
    except (ValueError, Exception):
        logger.debug("Visitor merge skipped", exc_info=True)

    token, expires_in = mint_session_jwt(user.id, user.wp_user_id, user.role)

    user_data = {
        "id": str(user.id),
        "wp_user_id": user.wp_user_id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
    }

    return AuthResponse(
        access_token=token,
        expires_in=expires_in,
        user=user_data,
    )


@auth_router.get("/me", response_model=UserPublic)
async def get_me(user=Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return UserPublic(
        id=str(user.id),
        wp_user_id=user.wp_user_id,
        email=user.email,
        display_name=user.display_name,
        age_range=user.age_range,
        skin_tone=user.skin_tone,
        style_preference=user.style_preference,
        preferred_collection=user.preferred_collection,
        favorite_metals=user.favorite_metals,
        favorite_styles=user.favorite_styles,
        role=user.role,
    )


@auth_router.post("/logout")
async def logout():
    """Client-side logout — stateless backend has no session to invalidate.

    Client should discard the JWT. This endpoint exists for API completeness
    and future token-blocklist support.
    """
    return JSONResponse(content={"status": "ok", "message": "Token discarded by client"})
