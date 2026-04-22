"""Pytest configuration and fixtures."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def _disable_rate_limiter_by_default():
    """Stop every test from hitting the real Upstash limiter.

    Since T211 removed the ENABLE_RATE_LIMIT flag, the limiter now always runs
    whenever REDIS_URL is configured — which it is in local .env for dev
    convenience. Tests should not count against production rate-limit budgets.

    Tests that specifically exercise the limiter patch `get_redis_client`
    themselves and override this.
    """
    with patch("app.middleware.rate_limiter.get_redis_client", return_value=None):
        yield


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def anyio_backend():
    """Use asyncio for async tests."""
    return "asyncio"


@pytest.fixture
async def async_client():
    """Async test client for async endpoints."""
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
