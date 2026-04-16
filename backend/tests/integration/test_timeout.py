"""T122: Integration test for 15s timeout middleware."""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.middleware.timeout import TimeoutMiddleware


@pytest.fixture
def timeout_app():
    """Create a minimal FastAPI app with the timeout middleware and a slow handler."""
    app = FastAPI()
    app.add_middleware(TimeoutMiddleware)

    @app.post("/chat")
    async def slow_chat():
        await asyncio.sleep(30)
        return {"reply": "should never reach here"}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


@pytest.mark.asyncio
async def test_408_on_slow_handler(timeout_app):
    """T122: /chat that takes >15s returns 408 with brand-safe fallback."""
    with patch("app.middleware.timeout.settings") as mock_settings:
        mock_settings.request_timeout_seconds = 1  # 1s for fast test

        transport = ASGITransport(app=timeout_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/chat", json={"message": "hello"})

        assert resp.status_code == 408
        body = resp.json()
        assert body["code"] == 408
        assert "temporary delay" in body["error"].lower()


@pytest.mark.asyncio
async def test_health_not_affected_by_timeout(timeout_app):
    """Non-chat endpoints bypass timeout middleware."""
    transport = ASGITransport(app=timeout_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
