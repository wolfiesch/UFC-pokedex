"""Tests for cache error handling."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from redis.exceptions import ConnectionError as RedisConnectionError
from backend.cache import CacheClient


@pytest.mark.asyncio
async def test_cache_only_catches_redis_errors():
    """Test that non-Redis exceptions are not suppressed."""
    # Create a mock Redis client
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(side_effect=ValueError("Not a Redis error"))
    cache = CacheClient(mock_redis)

    # Should NOT suppress non-Redis exceptions
    with pytest.raises(ValueError):
        await cache.get_json("test_key")


@pytest.mark.asyncio
async def test_cache_handles_redis_connection_error():
    """Test that Redis connection errors are properly handled."""
    # Create a mock Redis client
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(side_effect=RedisConnectionError("Connection failed"))
    cache = CacheClient(mock_redis)

    # Should handle gracefully and return None
    result = await cache.get_json("test_key")
    assert result is None
