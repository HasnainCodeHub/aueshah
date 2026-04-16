"""T136: Async persistence writer — fire-and-forget chat + activity writes."""
import uuid
import logging
from typing import Optional

from app.db.session import get_session_factory
from app.db.repositories import chat_history as chat_repo

logger = logging.getLogger(__name__)


async def persist_turn(
    *,
    user_id: Optional[uuid.UUID],
    visitor_id: uuid.UUID,
    session_id: uuid.UUID,
    user_message: str,
    assistant_reply: str,
    intent: Optional[str] = None,
    skill: Optional[str] = None,
    routing_source: Optional[str] = None,
    latency_ms: Optional[int] = None,
    rag_chunk_ids: Optional[list[str]] = None,
) -> None:
    """Persist both user message and assistant reply to chat_messages. Best-effort — never raises."""
    factory = get_session_factory()
    if factory is None:
        logger.debug("DB not configured — skipping chat persistence")
        return

    try:
        async with factory() as session:
            await chat_repo.insert_message(
                session,
                user_id=user_id,
                visitor_id=visitor_id,
                session_id=session_id,
                role="user",
                content=user_message,
                intent=intent,
            )

            await chat_repo.insert_message(
                session,
                user_id=user_id,
                visitor_id=visitor_id,
                session_id=session_id,
                role="assistant",
                content=assistant_reply,
                intent=intent,
                skill=skill,
                routing_source=routing_source,
                latency_ms=latency_ms,
                rag_chunk_ids=rag_chunk_ids,
            )

        logger.debug(
            "Chat turn persisted",
            extra={"user_id": str(user_id), "visitor_id": str(visitor_id), "intent": intent},
        )
    except Exception:
        logger.warning("Failed to persist chat turn — continuing without DB", exc_info=True)


async def log_activity(
    *,
    user_id: uuid.UUID,
    activity_type: str,
    details: Optional[dict] = None,
) -> None:
    """Write a user_activity row. Best-effort — never raises."""
    factory = get_session_factory()
    if factory is None:
        return

    try:
        from app.db.models import UserActivity

        async with factory() as session:
            activity = UserActivity(
                user_id=user_id,
                activity_type=activity_type,
                details=details or {},
            )
            session.add(activity)
            await session.commit()
    except Exception:
        logger.warning("Failed to log activity — continuing", exc_info=True)
