"""Tests verifying Redis backoff retry behavior in the cache layer."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar, List

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from backend import cache


@dataclass
class _StubRedis:
    """Tiny Redis stand-in that can emulate connection failures for testing."""

    should_fail: bool
    closed: bool = False

    async def ping(self) -> None:
        """Raise a connection error when configured to do so."""
        if self.should_fail:
            raise RedisConnectionError("Redis unavailable for test")

    async def aclose(self) -> None:
        """Mark the client as closed to assert clean-up behavior."""
        self.closed = True


class _StubRedisFactory:
    """Factory that mimics :meth:`redis.Redis.from_url` with queued outcomes."""

    failures: ClassVar[List[bool]] = []
    created_clients: ClassVar[list[_StubRedis]] = []
    on_instantiate: ClassVar[Callable[[], None] | None] = None

    @classmethod
    def from_url(cls, *_: object, **__: object) -> _StubRedis:
        """Return a stub client whose ``ping`` outcome matches the configured queue."""
        if cls.on_instantiate is not None:
            cls.on_instantiate()
        should_fail = cls.failures.pop(0)
        client = _StubRedis(should_fail=should_fail)
        cls.created_clients.append(client)
        return client


@pytest.mark.asyncio
async def test_get_redis_retries_after_cooldown(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    request: pytest.FixtureRequest,
) -> None:
    """Redis connection attempts resume after the configured cool-down expires."""

    await cache.close_redis()
    _StubRedisFactory.failures = [True, False]
    _StubRedisFactory.created_clients = []

    # Guard against unexpected reconnect attempts by counting instantiations.
    attempts: dict[str, int] = {"count": 0}

    def _increment_attempts() -> None:
        attempts["count"] += 1

    _StubRedisFactory.on_instantiate = _increment_attempts

    monkeypatch.setattr(
        cache,
        "_load_redis_components",
        lambda: (_StubRedisFactory, RedisConnectionError),
    )
    monkeypatch.setattr(
        cache,
        "_is_redis_connection_error",
        lambda exc: isinstance(exc, RedisConnectionError),
    )

    current_time: dict[str, float] = {"value": 0.0}

    def fake_monotonic() -> float:
        return current_time["value"]

    monkeypatch.setattr(cache.time, "monotonic", fake_monotonic)
    caplog.set_level(logging.DEBUG)

    # First attempt fails and schedules a backoff window.
    first_result = await cache.get_redis()
    assert first_result is None
    assert attempts["count"] == 1
    assert cache._redis_disabled is not None  # type: ignore[attr-defined]
    assert "Retrying after" in " ".join(caplog.messages)

    # During the cool-down no new attempt should be made.
    current_time["value"] = 5.0
    second_result = await cache.get_redis()
    assert second_result is None
    assert attempts["count"] == 1  # no additional instantiation occurred

    # After the cool-down the client should reconnect successfully.
    current_time["value"] = 45.0
    third_result = await cache.get_redis()
    assert third_result is not None
    assert attempts["count"] == 2
    assert cache._redis_disabled is None  # type: ignore[attr-defined]

    await cache.close_redis()
    _StubRedisFactory.on_instantiate = None


@pytest.mark.asyncio
async def test_close_redis_clears_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Closing the cache connection also resets any pending backoff metadata."""

    await cache.close_redis()
    _StubRedisFactory.failures = [True]
    _StubRedisFactory.created_clients = []
    _StubRedisFactory.on_instantiate = None

    monkeypatch.setattr(
        cache,
        "_load_redis_components",
        lambda: (_StubRedisFactory, RedisConnectionError),
    )
    monkeypatch.setattr(
        cache,
        "_is_redis_connection_error",
        lambda exc: isinstance(exc, RedisConnectionError),
    )
    monkeypatch.setattr(cache.time, "monotonic", lambda: 0.0)

    await cache.get_redis()
    assert cache._redis_disabled is not None  # type: ignore[attr-defined]

    await cache.close_redis()
    assert cache._redis_disabled is None  # type: ignore[attr-defined]
