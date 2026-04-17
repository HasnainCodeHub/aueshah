"""T205/T206: Prometheus metrics endpoint + counters."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_metrics_endpoint_requires_admin_token():
    from app.main import app
    from app.config.settings import settings

    original = settings.admin_api_token
    settings.admin_api_token = "metric-secret"

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            unauth = await ac.get("/v1/admin/metrics")
            assert unauth.status_code == 401

            ok = await ac.get("/v1/admin/metrics", headers={"X-Admin-Token": "metric-secret"})
            assert ok.status_code == 200
            assert "text/plain" in ok.headers["content-type"]
            # Standard Prometheus exposition lines
            assert "chat_requests_total" in ok.text or "# HELP" in ok.text
    finally:
        settings.admin_api_token = original


@pytest.mark.asyncio
async def test_chat_increments_request_counter():
    """A successful /chat call must move chat_requests_total."""
    from app.api import routes as routes_mod
    from app.main import app
    from app.models.schemas import ChatResponse
    from app.utils.metrics import CHAT_REQUESTS_TOTAL

    async def _handle(self, request, *, personalization_preamble=None, **kwargs):  # noqa: ARG001
        return ChatResponse(reply="ok", metadata={"intent": "general", "skill": "general"})

    before = CHAT_REQUESTS_TOTAL.labels(intent="general", result="ok")._value.get()

    with patch.object(routes_mod.Orchestrator, "handle_chat", new=_handle), patch(
        "app.api.routes.persist_turn", new_callable=AsyncMock
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            await ac.post("/chat", json={"message": "hi"})

    after = CHAT_REQUESTS_TOTAL.labels(intent="general", result="ok")._value.get()
    assert after == before + 1
