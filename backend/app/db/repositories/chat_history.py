"""T134: Chat history repository — insert + query against chat_messages table."""
import uuid
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatMessage

logger = logging.getLogger(__name__)


async def insert_message(
    session: AsyncSession,
    *,
    user_id: Optional[uuid.UUID],
    visitor_id: uuid.UUID,
    session_id: uuid.UUID,
    role: str,
    content: str,
    intent: Optional[str] = None,
    skill: Optional[str] = None,
    routing_source: Optional[str] = None,
    latency_ms: Optional[int] = None,
    rag_chunk_ids: Optional[list[str]] = None,
) -> ChatMessage:
    """Insert a single chat message row."""
    msg = ChatMessage(
        user_id=user_id,
        visitor_id=visitor_id,
        session_id=session_id,
        role=role,
        content=content,
        intent=intent,
        skill=skill,
        routing_source=routing_source,
        latency_ms=latency_ms,
        rag_chunk_ids=rag_chunk_ids or [],
    )
    session.add(msg)
    await session.commit()
    return msg


async def get_recent_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 10,
) -> list[ChatMessage]:
    """Fetch the most recent N messages for a user, ordered oldest-first."""
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = list(result.scalars().all())
    rows.reverse()
    return rows


async def get_recent_for_visitor(
    session: AsyncSession,
    visitor_id: uuid.UUID,
    limit: int = 10,
) -> list[ChatMessage]:
    """Fetch the most recent N messages for an anonymous visitor."""
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.visitor_id == visitor_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = list(result.scalars().all())
    rows.reverse()
    return rows


async def get_last_intent(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> Optional[str]:
    """Get the intent of the user's most recent assistant message."""
    stmt = (
        select(ChatMessage.intent)
        .where(ChatMessage.user_id == user_id, ChatMessage.role == "assistant")
        .order_by(ChatMessage.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return row


async def merge_visitor_to_user(
    session: AsyncSession,
    visitor_id: uuid.UUID,
    user_id: uuid.UUID,
) -> int:
    """Rewrite anonymous messages to belong to an authenticated user. Returns count updated."""
    stmt = (
        update(ChatMessage)
        .where(ChatMessage.visitor_id == visitor_id, ChatMessage.user_id.is_(None))
        .values(user_id=user_id)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount
