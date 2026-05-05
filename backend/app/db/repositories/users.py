"""T147: User repository — upsert from WP claims, lookup, update last_seen."""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Appointment,
    ChatMessage,
    NoorAllocationRequest,
    User,
    UserActivity,
)

logger = logging.getLogger(__name__)


async def upsert_from_wp_claims(
    session: AsyncSession,
    *,
    wp_user_id: int,
    email: str,
    display_name: str,
) -> User:
    """Find-or-create a local user from WordPress claims. Updates profile on every login.

    Looks up by wp_user_id first, then falls back to email — handles cases where
    a WP user was deleted + recreated (new wp_user_id, same email) or where a
    legacy row has a stale/missing wp_user_id. On email match we reconcile
    wp_user_id rather than INSERTing and tripping the email unique constraint.
    """
    stmt = select(User).where(User.wp_user_id == wp_user_id)
    user = (await session.execute(stmt)).scalar_one_or_none()

    if user is None:
        stmt = select(User).where(User.email == email)
        user = (await session.execute(stmt)).scalar_one_or_none()

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
        user.wp_user_id = wp_user_id
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


async def update_profile(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    age_range: Optional[str] = None,
    skin_tone: Optional[str] = None,
    style_preference: Optional[str] = None,
    preferred_collection: Optional[str] = None,
    favorite_metals: Optional[list[str]] = None,
    favorite_styles: Optional[list[str]] = None,
    display_name: Optional[str] = None,
) -> Optional[User]:
    """Patch user profile fields — only writes the keys explicitly passed."""
    values: dict = {}
    if age_range is not None:
        values["age_range"] = age_range
    if skin_tone is not None:
        values["skin_tone"] = skin_tone
    if style_preference is not None:
        values["style_preference"] = style_preference
    if preferred_collection is not None:
        values["preferred_collection"] = preferred_collection
    if favorite_metals is not None:
        values["favorite_metals"] = favorite_metals
    if favorite_styles is not None:
        values["favorite_styles"] = favorite_styles
    if display_name is not None:
        values["display_name"] = display_name

    if not values:
        return await get_by_id(session, user_id)

    stmt = update(User).where(User.id == user_id).values(**values)
    await session.execute(stmt)
    await session.commit()
    return await get_by_id(session, user_id)


async def delete_user_pii(session: AsyncSession, user_id: uuid.UUID) -> dict:
    """T204: Hard-delete all PII for a user (GDPR right-to-erasure).

    Removes rows from chat_messages, appointments, noor_allocation_requests,
    user_activity, and the users table itself. Returns a summary of deleted
    row counts per table for audit.

    Chat messages still tied to an anonymous visitor_id (user_id IS NULL) are
    not affected — they are not attributable to an identified person.
    """
    user = await get_by_id(session, user_id)
    if user is None:
        return {"deleted": False, "reason": "user_not_found"}

    counts: dict[str, int] = {}

    for table_name, stmt in [
        ("chat_messages", delete(ChatMessage).where(ChatMessage.user_id == user_id)),
        ("appointments", delete(Appointment).where(Appointment.user_id == user_id)),
        (
            "noor_allocation_requests",
            delete(NoorAllocationRequest).where(NoorAllocationRequest.user_id == user_id),
        ),
        ("user_activity", delete(UserActivity).where(UserActivity.user_id == user_id)),
        ("users", delete(User).where(User.id == user_id)),
    ]:
        result = await session.execute(stmt)
        counts[table_name] = result.rowcount or 0

    await session.commit()
    logger.warning("PII deleted", extra={"user_id": str(user_id), "counts": counts})
    return {"deleted": True, "counts": counts}
