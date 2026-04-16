"""T132: Unit tests for visitor cookie issuance and validation."""
import pytest
from unittest.mock import MagicMock

from app.auth.visitor import get_visitor_id, set_visitor_cookie, _sign, _verify


def test_new_visitor_gets_uuid():
    """No cookie present → new UUID generated."""
    request = MagicMock()
    request.cookies = {}
    vid = get_visitor_id(request)
    assert len(vid) == 36  # uuid4 string
    assert "-" in vid


def test_valid_cookie_returns_same_id():
    """Valid signed cookie → returns the original visitor_id."""
    original = "550e8400-e29b-41d4-a716-446655440000"
    signed = _sign(original)

    request = MagicMock()
    request.cookies = {"aueshah_visitor_id": signed}
    vid = get_visitor_id(request)
    assert vid == original


def test_tampered_cookie_issues_new():
    """Tampered cookie → new UUID issued instead."""
    signed = _sign("real-id") + "tampered"

    request = MagicMock()
    request.cookies = {"aueshah_visitor_id": signed}
    vid = get_visitor_id(request)
    assert vid != "real-id"
    assert len(vid) == 36


def test_sign_verify_roundtrip():
    vid = "test-visitor-123"
    signed = _sign(vid)
    assert _verify(signed) == vid


def test_verify_rejects_no_dot():
    assert _verify("no-dot-here") is None


def test_set_cookie_on_response():
    response = MagicMock()
    set_visitor_cookie(response, "my-visitor-id")
    response.set_cookie.assert_called_once()
    call_kwargs = response.set_cookie.call_args
    assert call_kwargs.kwargs["key"] == "aueshah_visitor_id"
    assert call_kwargs.kwargs["httponly"] is True
    assert "my-visitor-id" in call_kwargs.kwargs["value"]
