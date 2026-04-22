"""Unit tests for WordPress HS256 JWT verification."""
import time
import pytest
from unittest.mock import patch

from jose import jwt as jose_jwt

from app.auth.wp_verifier import verify_wp_token, WPClaims
from app.models.errors import AuthFailure


TEST_SECRET = "test-hs256-secret-key-abc123"


def _sign(claims: dict, secret: str = TEST_SECRET) -> str:
    return jose_jwt.encode(claims, secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_verify_valid_token_with_nested_claims():
    """Chávez-style plugin nests user id under data.user.id."""
    now = int(time.time())
    token = _sign({
        "iss": "https://aueshah.com",
        "iat": now,
        "nbf": now,
        "exp": now + 3600,
        "data": {"user": {"id": 42}},
    })

    with patch("app.auth.wp_verifier.settings") as ms:
        ms.wp_jwt_secret = TEST_SECRET
        ms.wp_issuer = "https://aueshah.com"
        ms.wp_base_url = ""
        claims = await verify_wp_token(token)

    assert isinstance(claims, WPClaims)
    assert claims.wp_user_id == 42


@pytest.mark.asyncio
async def test_verify_valid_token_with_flat_claims():
    """Some plugin variants put fields at the top level."""
    now = int(time.time())
    token = _sign({
        "iss": "https://aueshah.com",
        "sub": 99,
        "email": "flat@aueshah.com",
        "display_name": "Flat User",
        "iat": now,
        "exp": now + 3600,
    })

    with patch("app.auth.wp_verifier.settings") as ms:
        ms.wp_jwt_secret = TEST_SECRET
        ms.wp_issuer = "https://aueshah.com"
        ms.wp_base_url = ""
        claims = await verify_wp_token(token)

    assert claims.wp_user_id == 99
    assert claims.email == "flat@aueshah.com"
    assert claims.display_name == "Flat User"


@pytest.mark.asyncio
async def test_verify_rejects_malformed():
    with patch("app.auth.wp_verifier.settings") as ms:
        ms.wp_jwt_secret = TEST_SECRET
        with pytest.raises(AuthFailure, match="Malformed token"):
            await verify_wp_token("not-a-jwt")


@pytest.mark.asyncio
async def test_verify_rejects_bad_signature():
    now = int(time.time())
    token = _sign({
        "iss": "https://aueshah.com",
        "sub": 1,
        "iat": now,
        "exp": now + 3600,
    }, secret="different-secret")

    with patch("app.auth.wp_verifier.settings") as ms:
        ms.wp_jwt_secret = TEST_SECRET
        ms.wp_issuer = ""
        with pytest.raises(AuthFailure, match="Token verification failed"):
            await verify_wp_token(token)


@pytest.mark.asyncio
async def test_verify_rejects_expired():
    token = _sign({
        "iss": "https://aueshah.com",
        "sub": 1,
        "iat": 1000000,
        "exp": 1000001,
    })

    with patch("app.auth.wp_verifier.settings") as ms:
        ms.wp_jwt_secret = TEST_SECRET
        ms.wp_issuer = ""
        with pytest.raises(AuthFailure, match="Token expired"):
            await verify_wp_token(token)


@pytest.mark.asyncio
async def test_verify_rejects_wrong_issuer():
    now = int(time.time())
    token = _sign({
        "iss": "https://evil.com",
        "sub": 1,
        "iat": now,
        "exp": now + 3600,
    })

    with patch("app.auth.wp_verifier.settings") as ms:
        ms.wp_jwt_secret = TEST_SECRET
        ms.wp_issuer = "https://aueshah.com"
        with pytest.raises(AuthFailure, match="Invalid token issuer"):
            await verify_wp_token(token)


@pytest.mark.asyncio
async def test_verify_hydrates_from_users_me():
    """When claims don't include email/display_name, fall back to /users/me."""
    now = int(time.time())
    token = _sign({
        "iss": "https://aueshah.com",
        "iat": now,
        "exp": now + 3600,
        "data": {"user": {"id": 7}},
    })

    async def fake_hydrate(_token):
        return {"name": "Hydrated User", "email": "hydrated@aueshah.com"}

    with patch("app.auth.wp_verifier.settings") as ms:
        ms.wp_jwt_secret = TEST_SECRET
        ms.wp_issuer = "https://aueshah.com"
        ms.wp_base_url = "https://aueshah.com"
        with patch("app.auth.wp_verifier._hydrate_from_users_me", side_effect=fake_hydrate):
            claims = await verify_wp_token(token)

    assert claims.wp_user_id == 7
    assert claims.email == "hydrated@aueshah.com"
    assert claims.display_name == "Hydrated User"


@pytest.mark.asyncio
async def test_verify_fails_when_secret_not_configured():
    with patch("app.auth.wp_verifier.settings") as ms:
        ms.wp_jwt_secret = ""
        with pytest.raises(AuthFailure, match="not configured"):
            await verify_wp_token("any.token.here")
