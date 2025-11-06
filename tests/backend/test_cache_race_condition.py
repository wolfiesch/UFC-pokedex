"""Tests for cache initialization race conditions."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from backend.cache import get_redis


@pytest.mark.asyncio
async def test_concurrent_cache_initialization():
    """Test that concurrent calls don't create multiple clients."""
    # Reset global state
    import backend.cache as cache_module
    original_client = cache_module._redis_client
    cache_module._redis_client = None

    # Track how many times Redis.from_url is called
    init_count = 0

    try:
        # Mock Redis client with ping method
        mock_client = MagicMock()
        mock_client.ping = AsyncMock(return_value=True)

        def tracked_from_url(*args, **kwargs):
            nonlocal init_count
            init_count += 1
            return mock_client

        # Mock Redis.from_url to track initialization attempts
        from redis.asyncio import Redis
        with patch.object(Redis, 'from_url', side_effect=tracked_from_url):
            # Simulate 10 concurrent initialization attempts
            results = await asyncio.gather(*[get_redis() for _ in range(10)])

            # All should return same client
            assert all(r == results[0] for r in results), "All calls should return same client"

            # Client should only be created once
            assert init_count == 1, f"Redis.from_url should be called exactly once, but was called {init_count} times"

    finally:
        # Restore original state
        cache_module._redis_client = original_client


@pytest.mark.asyncio
async def test_race_condition_window():
    """Test for TOCTOU race condition in get_redis.

    The bug: Early return `if _redis_client is None` check happens BEFORE lock acquisition.
    This creates a TOCTOU window where multiple coroutines can see None and enter the lock block.
    """
    import backend.cache as cache_module
    original_client = cache_module._redis_client
    original_lock = cache_module._client_lock
    cache_module._redis_client = None

    # Use a new lock for this test to avoid interference
    cache_module._client_lock = asyncio.Lock()

    initialization_count = 0

    try:
        # Create a mock that tracks calls
        mock_client = MagicMock()
        mock_client.ping = AsyncMock(return_value=True)

        def count_from_url(*args, **kwargs):
            nonlocal initialization_count
            initialization_count += 1
            return mock_client

        from redis.asyncio import Redis

        # Patch both from_url and the module's _redis_url to avoid env dependency
        with patch.object(Redis, 'from_url', side_effect=count_from_url), \
             patch('backend.cache._redis_url', return_value='redis://localhost:6379/0'):

            # The current code has this pattern:
            #   if _redis_client is None:  <-- TOCTOU window here!
            #       async with _lock:
            #           if _redis_client is None:
            #               ... initialize ...
            #
            # Both coroutines can pass the first check before either acquires the lock

            # Launch tasks truly concurrently
            tasks = [asyncio.create_task(get_redis()) for _ in range(5)]
            results = await asyncio.gather(*tasks)

            # All should return the same client
            assert all(r == results[0] for r in results), "All calls should return same client"

            # The double-check locking SHOULD prevent multiple initializations,
            # but if there's any possibility of the race, this test should catch it.
            # With the current code, the race is prevented by the inner check.
            # But the task description says we should move the lock BEFORE the first check.
            assert initialization_count == 1, \
                f"Should initialize only once, got {initialization_count} initializations"

    finally:
        # Restore original state
        cache_module._redis_client = original_client
        cache_module._client_lock = original_lock
