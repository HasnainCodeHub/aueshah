"""T204: Tests for the GDPR right-to-erasure endpoint."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_pii_deletion_requires_admin_token():
    """DELETE /v1/admin/users/{id} without token → 401."""
    from app.db.session import get_session
    from app.main import app

    async def _session_override():
        yield MagicMock()

    app.dependency_overrides[get_session] = _session_override
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.delete(f"/v1/admin/users/{uuid.uuid4()}")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_pii_deletion_with_token_returns_counts():
    """Valid token + existing user → 200 with per-table deletion counts."""
    from app.config.settings import settings
    from app.db.session import get_session
    from app.main import app

    async def _session_override():
        yield MagicMock()

    app.dependency_overrides[get_session] = _session_override

    user_id = uuid.uuid4()
    original_token = settings.admin_api_token
    settings.admin_api_token = "test-secret"

    fake_result = {
        "deleted": True,
        "counts": {
            "chat_messages": 12,
            "appointments": 1,
            "noor_allocation_requests": 0,
            "user_activity": 4,
            "users": 1,
        },
    }

    try:
        with patch(
            "app.api.admin_routes.user_repo.delete_user_pii",
            new_callable=AsyncMock,
            return_value=fake_result,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.delete(
                    f"/v1/admin/users/{user_id}",
                    headers={"X-Admin-Token": "test-secret"},
                )
    finally:
        settings.admin_api_token = original_token
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["deleted"] is True
    assert body["user_id"] == str(user_id)
    assert body["counts"]["chat_messages"] == 12
    assert body["counts"]["users"] == 1


@pytest.mark.asyncio
async def test_pii_deletion_missing_user_returns_not_found_body():
    """Valid token + unknown user → 200 with deleted=False reason=user_not_found."""
    from app.config.settings import settings
    from app.db.session import get_session
    from app.main import app

    async def _session_override():
        yield MagicMock()

    app.dependency_overrides[get_session] = _session_override

    original_token = settings.admin_api_token
    settings.admin_api_token = "test-secret"

    try:
        with patch(
            "app.api.admin_routes.user_repo.delete_user_pii",
            new_callable=AsyncMock,
            return_value={"deleted": False, "reason": "user_not_found"},
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.delete(
                    f"/v1/admin/users/{uuid.uuid4()}",
                    headers={"X-Admin-Token": "test-secret"},
                )
    finally:
        settings.admin_api_token = original_token
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["deleted"] is False
    assert body["reason"] == "user_not_found"
