"""T120-T121: Integration tests for Redis sliding-window rate limiter."""
import pytest
from unittest.mock import AsyncMock, patch

from app.middleware.rate_limiter import check_rate_limit, get_redis_client
from app.models.errors import RateLimited


@pytest.fixture
def mock_redis():
    """Create a fake Redis pipeline that tracks call counts per IP."""
    counts = {}

    class FakePipeline:
        def __init__(self, ip_key):
            self._ip_key = ip_key

        def zremrangebyscore(self, key, start, end):
            pass

        def zadd(self, key, mapping):
            counts[self._ip_key] = counts.get(self._ip_key, 0) + 1

        def zcard(self, key):
            pass

        def expire(self, key, ttl):
            pass

        async def execute(self):
            return [0, 1, counts.get(self._ip_key, 1), True]

    class FakeRedis:
        def pipeline(self, transaction=False):
            return FakePipeline("test")

    return FakeRedis(), counts


@pytest.mark.asyncio
async def test_429_after_5_requests(mock_redis):
    """T120: Fire 6 requests — first 5 pass, 6th raises RateLimited."""
    fake_redis, counts = mock_redis

    with patch("app.middleware.rate_limiter.get_redis_client", return_value=fake_redis), \
         patch("app.middleware.rate_limiter.settings") as mock_settings:
        mock_settings.enable_rate_limit = True
        mock_settings.rate_limit_per_min = 5
        mock_settings.redis_url = "redis://fake"

        for i in range(5):
            await check_rate_limit("1.2.3.4")

        with pytest.raises(RateLimited):
            await check_rate_limit("1.2.3.4")


@pytest.mark.asyncio
async def test_redis_down_fail_open():
    """T121: When Redis is unreachable, requests pass through with a warning."""
    failing_redis = AsyncMock()
    failing_redis.pipeline.side_effect = ConnectionError("Redis down")

    with patch("app.middleware.rate_limiter.get_redis_client", return_value=failing_redis), \
         patch("app.middleware.rate_limiter.settings") as mock_settings:
        mock_settings.enable_rate_limit = True
        mock_settings.rate_limit_per_min = 5
        mock_settings.redis_url = "redis://fake"

        # Should NOT raise — fail-open
        await check_rate_limit("1.2.3.4")


@pytest.mark.asyncio
async def test_rate_limit_disabled_allows_all():
    """When ENABLE_RATE_LIMIT is False, all requests pass."""
    with patch("app.middleware.rate_limiter.settings") as mock_settings:
        mock_settings.enable_rate_limit = False

        for _ in range(100):
            await check_rate_limit("1.2.3.4")


@pytest.mark.asyncio
async def test_no_redis_url_allows_all():
    """When REDIS_URL is empty, all requests pass."""
    with patch("app.middleware.rate_limiter._redis_client", None), \
         patch("app.middleware.rate_limiter.settings") as mock_settings:
        mock_settings.enable_rate_limit = True
        mock_settings.redis_url = ""

        await check_rate_limit("1.2.3.4")
