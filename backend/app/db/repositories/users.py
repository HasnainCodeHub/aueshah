"""T147: User repository — upsert from WP claims, lookup, update last_seen."""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User

logger = logging.getLogger(__name__)


async def upsert_from_wp_claims(
    session: AsyncSession,
    *,
    wp_user_id: int,
    email: str,
    display_name: str,
) -> User:
    """Find-or-create a local user from WordPress claims. Updates profile on every login."""
    stmt = select(User).where(User.wp_user_id == wp_user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            wp_user_id=wp_user_id,
            email=email,
            display_name=display_name,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("New user created from WP login", extra={"wp_user_id": wp_user_id})
    else:
        user.email = email
        user.display_name = display_name
        user.last_seen_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(user)

    return user


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_last_seen(session: AsyncSession, user_id: uuid.UUID) -> None:
    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(last_seen_at=datetime.now(timezone.utc))
    )
    await session.execute(stmt)
    await session.commit()
