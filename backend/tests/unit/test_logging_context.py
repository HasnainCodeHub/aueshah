"""T207: Verify the JSON formatter picks up ContextVar request_id and extras."""
import json
import logging
from io import StringIO

import pytest

from app.utils.logging import JSONFormatter, set_request_context, reset_request_context


def _capture(record_extra=None):
    logger = logging.getLogger("test.logging")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    buf = StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    return logger, buf


def test_request_id_appears_in_log():
    tokens = set_request_context(request_id="req-abc123", user_id="u-1")
    try:
        logger, buf = _capture()
        logger.info("hello", extra={"intent": "noor", "skill": "noor", "latency_ms": 42})
        line = buf.getvalue().strip()
        obj = json.loads(line)
        assert obj["request_id"] == "req-abc123"
        assert obj["user_id"] == "u-1"
        assert obj["intent"] == "noor"
        assert obj["latency_ms"] == 42
        assert obj["level"] == "INFO"
    finally:
        reset_request_context(tokens)


def test_no_request_id_when_unset():
    logger, buf = _capture()
    logger.info("hello")
    obj = json.loads(buf.getvalue().strip())
    assert "request_id" not in obj
    assert "user_id" not in obj


def test_unserializable_extras_dropped():
    """Non-JSON-serializable extras must not crash the formatter."""
    logger, buf = _capture()
    logger.info("with bad extra", extra={"weird": object()})
    line = buf.getvalue().strip()
    # Should still be valid JSON.
    obj = json.loads(line)
    assert obj["message"] == "with bad extra"


@pytest.mark.asyncio
async def test_middleware_stamps_request_id_header():
    """The middleware must echo X-Request-ID and respect inbound override."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Inbound override
        resp = await ac.get("/health", headers={"X-Request-ID": "trace-XYZ"})
        assert resp.status_code == 200
        assert resp.headers["X-Request-ID"] == "trace-XYZ"

        # Mint when missing
        resp = await ac.get("/health")
        assert resp.status_code == 200
        assert "X-Request-ID" in resp.headers
        assert len(resp.headers["X-Request-ID"]) >= 8
