"""T141: Unit tests for session JWT minting and decoding."""
import uuid
import time
import pytest
from unittest.mock import patch

from app.auth.session_jwt import mint_session_jwt, decode_session_jwt
from app.models.errors import AuthFailure


FAKE_KEY = "test-secret-key-at-least-32-chars-long"


@patch("app.auth.session_jwt.settings")
def test_mint_and_decode_roundtrip(mock_settings):
    mock_settings.jwt_signing_key = FAKE_KEY
    mock_settings.jwt_expires_seconds = 3600

    user_id = uuid.uuid4()
    token, expires_in = mint_session_jwt(user_id, wp_user_id=42, role="client")

    assert expires_in == 3600
    assert isinstance(token, str)

    payload = decode_session_jwt(token)
    assert payload["sub"] == str(user_id)
    assert payload["wp_uid"] == 42
    assert payload["role"] == "client"


@patch("app.auth.session_jwt.settings")
def test_decode_rejects_expired(mock_settings):
    mock_settings.jwt_signing_key = FAKE_KEY
    mock_settings.jwt_expires_seconds = -100  # already expired

    user_id = uuid.uuid4()
    token, _ = mint_session_jwt(user_id, wp_user_id=1, role="client")

    with pytest.raises(AuthFailure, match="Session expired"):
        decode_session_jwt(token)


@patch("app.auth.session_jwt.settings")
def test_decode_rejects_wrong_key(mock_settings):
    mock_settings.jwt_signing_key = FAKE_KEY
    mock_settings.jwt_expires_seconds = 3600

    token, _ = mint_session_jwt(uuid.uuid4(), wp_user_id=1)

    mock_settings.jwt_signing_key = "different-key-also-at-least-32-chars"
    with pytest.raises(AuthFailure, match="Invalid session token"):
        decode_session_jwt(token)


@patch("app.auth.session_jwt.settings")
def test_decode_rejects_garbage(mock_settings):
    mock_settings.jwt_signing_key = FAKE_KEY
    with pytest.raises(AuthFailure, match="Invalid session token"):
        decode_session_jwt("not.a.jwt")


@patch("app.auth.session_jwt.settings")
def test_mint_raises_when_no_key(mock_settings):
    mock_settings.jwt_signing_key = ""
    with pytest.raises(AuthFailure, match="signing key not configured"):
        mint_session_jwt(uuid.uuid4(), wp_user_id=1)
