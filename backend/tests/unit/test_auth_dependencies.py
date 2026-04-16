"""T143: Unit tests for auth dependencies."""
import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.auth.dependencies import _extract_bearer, get_current_user, get_current_user_optional
from app.models.errors import AuthFailure


def test_extract_bearer_valid():
    request = MagicMock()
    request.headers = {"Authorization": "Bearer abc123"}
    assert _extract_bearer(request) == "abc123"


def test_extract_bearer_missing():
    request = MagicMock()
    request.headers = {}
    assert _extract_bearer(request) is None


def test_extract_bearer_wrong_scheme():
    request = MagicMock()
    request.headers = {"Authorization": "Basic abc123"}
    assert _extract_bearer(request) is None


@pytest.mark.asyncio
async def test_get_current_user_no_header():
    request = MagicMock()
    request.headers = {}
    with pytest.raises(AuthFailure, match="Authorization header required"):
        await get_current_user(request, session=MagicMock())


@pytest.mark.asyncio
async def test_get_current_user_optional_no_header():
    request = MagicMock()
    request.headers = {}
    result = await get_current_user_optional(request, session=MagicMock())
    assert result is None


@pytest.mark.asyncio
async def test_get_current_user_optional_bad_token():
    request = MagicMock()
    request.headers = {"Authorization": "Bearer bad-token"}

    with patch("app.auth.dependencies.decode_session_jwt", side_effect=AuthFailure("bad")):
        result = await get_current_user_optional(request, session=MagicMock())
    assert result is None


@pytest.mark.asyncio
async def test_get_current_user_valid():
    user_id = uuid.uuid4()
    mock_user = MagicMock()
    mock_user.id = user_id

    request = MagicMock()
    request.headers = {"Authorization": "Bearer good-token"}

    with patch("app.auth.dependencies.decode_session_jwt", return_value={"sub": str(user_id)}):
        with patch("app.auth.dependencies.user_repo") as mock_repo:
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)
            result = await get_current_user(request, session=MagicMock())

    assert result == mock_user


@pytest.mark.asyncio
async def test_get_current_user_not_in_db():
    user_id = uuid.uuid4()
    request = MagicMock()
    request.headers = {"Authorization": "Bearer good-token"}

    with patch("app.auth.dependencies.decode_session_jwt", return_value={"sub": str(user_id)}):
        with patch("app.auth.dependencies.user_repo") as mock_repo:
            mock_repo.get_by_id = AsyncMock(return_value=None)
            with pytest.raises(AuthFailure, match="User not found"):
                await get_current_user(request, session=MagicMock())
