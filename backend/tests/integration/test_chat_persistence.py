"""T130-T131: Integration tests for chat persistence (Group B)."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_persist_turn_skips_when_no_db():
    """T131: When DB is not configured, persist_turn logs debug and returns silently."""
    with patch("app.services.persistence_writer.get_session_factory", return_value=None):
        from app.services.persistence_writer import persist_turn
        import uuid

        # Should NOT raise
        await persist_turn(
            user_id=None,
            visitor_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            user_message="hello",
            assistant_reply="hi there",
            intent="general",
            skill="general",
        )


@pytest.mark.asyncio
async def test_persist_turn_catches_db_errors():
    """T131: When DB raises, persist_turn catches and logs warning — never propagates."""
    mock_factory = MagicMock()
    mock_session = AsyncMock()
    mock_session.commit.side_effect = Exception("DB connection lost")
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_factory.return_value = mock_session

    with patch("app.services.persistence_writer.get_session_factory", return_value=mock_factory):
        from app.services.persistence_writer import persist_turn
        import uuid

        # Should NOT raise even though DB explodes
        await persist_turn(
            user_id=None,
            visitor_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            user_message="hello",
            assistant_reply="hi",
        )


@pytest.mark.asyncio
async def test_log_activity_skips_when_no_db():
    """User activity logging silently skips when no DB configured."""
    with patch("app.services.persistence_writer.get_session_factory", return_value=None):
        from app.services.persistence_writer import log_activity
        import uuid

        await log_activity(
            user_id=uuid.uuid4(),
            activity_type="chat_message",
            details={"intent": "noor"},
        )


@pytest.mark.asyncio
async def test_log_activity_catches_errors():
    """User activity logging catches DB errors silently."""
    mock_factory = MagicMock()
    mock_session = AsyncMock()
    mock_session.commit.side_effect = Exception("DB down")
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_factory.return_value = mock_session

    with patch("app.services.persistence_writer.get_session_factory", return_value=mock_factory):
        from app.services.persistence_writer import log_activity
        import uuid

        await log_activity(
            user_id=uuid.uuid4(),
            activity_type="noor_request_submitted",
            details={"ref": "NOR-ABC123"},
        )
