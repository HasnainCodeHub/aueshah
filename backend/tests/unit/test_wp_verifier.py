"""T142: Unit tests for WordPress JWT verification."""
import time
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from jose import jwt as jose_jwt

from app.auth.wp_verifier import verify_wp_token, clear_jwks_cache, WPClaims
from app.models.errors import AuthFailure

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from jose import jwk


def _make_rsa_pair():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key()
    pub_pem = public.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    priv_pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_jwk = jwk.RSAKey(algorithm="RS256", key=pub_pem.decode()).to_dict()
    pub_jwk["kid"] = "test-kid"
    pub_jwk["use"] = "sig"
    return priv_pem, pub_jwk


def _sign_wp_token(priv_pem, claims, kid="test-kid"):
    return jose_jwt.encode(claims, priv_pem.decode(), algorithm="RS256", headers={"kid": kid})


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_jwks_cache()
    yield
    clear_jwks_cache()


@pytest.mark.asyncio
async def test_verify_valid_wp_token():
    priv_pem, pub_jwk = _make_rsa_pair()
    now = int(time.time())
    token = _sign_wp_token(priv_pem, {
        "iss": "https://aueshah.com",
        "sub": 42,
        "email": "test@aueshah.com",
        "display_name": "Test User",
        "iat": now,
        "exp": now + 3600,
    })

    async def mock_fetch():
        return {"test-kid": pub_jwk}

    with patch("app.auth.wp_verifier._fetch_jwks", side_effect=mock_fetch):
        with patch("app.auth.wp_verifier.settings") as mock_settings:
            mock_settings.wp_issuer = "https://aueshah.com"
            claims = await verify_wp_token(token)

    assert isinstance(claims, WPClaims)
    assert claims.wp_user_id == 42
    assert claims.email == "test@aueshah.com"
    assert claims.display_name == "Test User"


@pytest.mark.asyncio
async def test_verify_nested_wp_claims():
    """WP JWT plugin sometimes nests claims under data.user."""
    priv_pem, pub_jwk = _make_rsa_pair()
    now = int(time.time())
    token = _sign_wp_token(priv_pem, {
        "iss": "https://aueshah.com",
        "iat": now,
        "exp": now + 3600,
        "data": {
            "user": {
                "id": 99,
                "email": "nested@aueshah.com",
                "display_name": "Nested User",
            }
        },
    })

    async def mock_fetch():
        return {"test-kid": pub_jwk}

    with patch("app.auth.wp_verifier._fetch_jwks", side_effect=mock_fetch):
        with patch("app.auth.wp_verifier.settings") as mock_settings:
            mock_settings.wp_issuer = "https://aueshah.com"
            claims = await verify_wp_token(token)

    assert claims.wp_user_id == 99
    assert claims.email == "nested@aueshah.com"


@pytest.mark.asyncio
async def test_verify_rejects_malformed():
    with pytest.raises(AuthFailure, match="Malformed token"):
        await verify_wp_token("not-a-jwt")


@pytest.mark.asyncio
async def test_verify_rejects_expired():
    priv_pem, pub_jwk = _make_rsa_pair()
    token = _sign_wp_token(priv_pem, {
        "iss": "https://aueshah.com",
        "sub": 1,
        "iat": 1000000,
        "exp": 1000001,
    })

    async def mock_fetch():
        return {"test-kid": pub_jwk}

    with patch("app.auth.wp_verifier._fetch_jwks", side_effect=mock_fetch):
        with patch("app.auth.wp_verifier.settings") as mock_settings:
            mock_settings.wp_issuer = ""
            with pytest.raises(AuthFailure, match="Token expired"):
                await verify_wp_token(token)


@pytest.mark.asyncio
async def test_verify_rejects_wrong_issuer():
    priv_pem, pub_jwk = _make_rsa_pair()
    now = int(time.time())
    token = _sign_wp_token(priv_pem, {
        "iss": "https://evil.com",
        "sub": 1,
        "iat": now,
        "exp": now + 3600,
    })

    async def mock_fetch():
        return {"test-kid": pub_jwk}

    with patch("app.auth.wp_verifier._fetch_jwks", side_effect=mock_fetch):
        with patch("app.auth.wp_verifier.settings") as mock_settings:
            mock_settings.wp_issuer = "https://aueshah.com"
            with pytest.raises(AuthFailure, match="Invalid token issuer"):
                await verify_wp_token(token)
