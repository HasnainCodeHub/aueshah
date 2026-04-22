"""Redis sliding-window rate limiter — 5 req/min/IP, fail-open on Redis errors."""
import logging
import time
import uuid

import redis.asyncio as aioredis

from app.config.settings import settings
from app.models.errors import RateLimited
from app.utils.metrics import RATE_LIMIT_HITS_TOTAL

logger = logging.getLogger(__name__)

_redis_client = None


def get_redis_client():
    global _redis_client
    if _redis_client is None and settings.redis_url:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis_client


async def close_redis():
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


async def check_rate_limit(client_ip: str) -> None:
    """Check sliding-window rate limit. Raises RateLimited if exceeded. Fails open on Redis errors."""
    client = get_redis_client()
    if client is None:
        return

    key = f"ratelimit:chat:{client_ip}"
    now = time.time()
    window_start = now - 60

    try:
        pipe = client.pipeline(transaction=False)
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(uuid.uuid4()): now})
        pipe.zcard(key)
        pipe.expire(key, 60)
        results = await pipe.execute()
        count = results[2]

        if count > settings.rate_limit_per_min:
            logger.warning(
                "Rate limit exceeded",
                extra={"ip": client_ip, "count": count, "limit": settings.rate_limit_per_min},
            )
            RATE_LIMIT_HITS_TOTAL.inc()
            raise RateLimited()

    except RateLimited:
        raise
    except Exception:
        logger.warning("Redis unavailable — failing open", extra={"ip": client_ip}, exc_info=True)
