"""Unit tests validating the cache module's error-handling behavior."""

from unittest.mock import AsyncMock, MagicMock

import pytest

import backend.cache as cache


@pytest.mark.asyncio
async def test_cache_only_catches_redis_errors():
    """Test that non-Redis exceptions are not suppressed."""
    # Create a mock Redis client with intentionally invalid behavior so the
    # cache client must propagate it without suppression.
    mock_redis = MagicMock()

    assert cache._is_redis_connection_error(cache.RedisConnectionError("probe"))
    mock_redis.get = AsyncMock(side_effect=ValueError("Not a Redis error"))
    cache_client = cache.CacheClient(mock_redis)

    # Should NOT suppress non-Redis exceptions
    with pytest.raises(ValueError):
        await cache_client.get_json("test_key")


@pytest.mark.asyncio
async def test_cache_handles_redis_connection_error():
    """Test that Redis connection errors are properly handled."""
    # Create a mock Redis client that raises a connection error to verify graceful degradation.
    mock_redis = MagicMock()

    assert cache._is_redis_connection_error(cache.RedisConnectionError("probe"))
    mock_redis.get = AsyncMock(
        side_effect=cache.RedisConnectionError("Connection failed")
    )
    cache_client = cache.CacheClient(mock_redis)

    # Should handle gracefully and return None
    result = await cache_client.get_json("test_key")
    assert result is None
