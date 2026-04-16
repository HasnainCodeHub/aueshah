"""T140/T144: Integration tests for auth routes (wp-login, /me, /logout)."""
import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.auth.wp_verifier import WPClaims
from app.db.session import get_session


def _mock_session_override():
    """FastAPI dependency override that yields a MagicMock session."""
    async def _gen():
        yield MagicMock()
    return _gen


@pytest.mark.asyncio
async def test_wp_login_success():
    """POST /v1/auth/wp-login with valid WP token returns our session JWT."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.wp_user_id = 42
    mock_user.email = "test@aueshah.com"
    mock_user.display_name = "Test User"
    mock_user.role = "client"

    wp_claims = WPClaims(sub=42, email="test@aueshah.com", display_name="Test User", raw={})

    app.dependency_overrides[get_session] = _mock_session_override()

    try:
        with patch("app.api.auth_routes.verify_wp_token", new_callable=AsyncMock, return_value=wp_claims), \
             patch("app.api.auth_routes.user_repo") as mock_repo, \
             patch("app.api.auth_routes.chat_repo") as mock_chat, \
             patch("app.api.auth_routes.mint_session_jwt", return_value=("fake-jwt", 86400)):

            mock_repo.upsert_from_wp_claims = AsyncMock(return_value=mock_user)
            mock_chat.merge_visitor_to_user = AsyncMock(return_value=0)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/v1/auth/wp-login", json={
                    "wp_token": "a-valid-wp-token-string",
                })
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] == "fake-jwt"
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == 86400
    assert data["user"]["email"] == "test@aueshah.com"


@pytest.mark.asyncio
async def test_wp_login_rejects_bad_token():
    """POST /v1/auth/wp-login with invalid WP token returns 401."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.models.errors import AuthFailure

    app.dependency_overrides[get_session] = _mock_session_override()

    try:
        with patch("app.api.auth_routes.verify_wp_token", new_callable=AsyncMock, side_effect=AuthFailure("Malformed token")):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/v1/auth/wp-login", json={
                    "wp_token": "bad-token-value",
                })
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_without_token():
    """GET /v1/auth/me without Authorization header returns 401."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/v1/auth/me")

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout():
    """POST /v1/auth/logout always returns 200 ok."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/v1/auth/logout")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
