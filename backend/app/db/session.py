"""Async SQLAlchemy engine and session factory for Neon Serverless Postgres."""
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import settings

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None and settings.neon_database_url:
        _engine = create_async_engine(
            settings.neon_database_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            # asyncpg requires statement_cache_size=0 for PgBouncer / Neon pooler
            connect_args={"statement_cache_size": 0},
        )
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        if engine is not None:
            _session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async DB session, auto-closes on exit."""
    factory = get_session_factory()
    if factory is None:
        logger.warning("Database not configured — yielding None session")
        yield None  # type: ignore[arg-type]
        return
    async with factory() as session:
        yield session


async def close_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
