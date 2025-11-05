from __future__ import annotations

import fnmatch
import json
import asyncio
import fnmatch
import json
import sys
import types
from collections.abc import AsyncIterator

import pytest

if "redis" not in sys.modules:
    redis_module = types.ModuleType("redis")
    asyncio_module = types.ModuleType("redis.asyncio")

    class _RedisStub:
        @classmethod
        def from_url(cls, *_args: object, **_kwargs: object) -> "_RedisStub":
            return cls()

    asyncio_module.Redis = _RedisStub  # type: ignore[attr-defined]
    sys.modules["redis"] = redis_module
    sys.modules["redis.asyncio"] = asyncio_module

    exceptions_module = types.ModuleType("redis.exceptions")

    class _ConnectionError(Exception):
        """Stubbed redis ConnectionError for offline test environments."""

    exceptions_module.ConnectionError = _ConnectionError  # type: ignore[attr-defined]
    sys.modules["redis.exceptions"] = exceptions_module

from backend.cache import (
    CacheClient,
    comparison_key,
    detail_key,
    event_detail_key,
    event_list_key,
    event_search_key,
    graph_key,
    list_key,
    related_events_key,
    search_key,
)


class InMemoryRedis:
    """Lightweight async Redis double used for cache client tests."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._ttl: dict[str, int | None] = {}

    async def ping(self) -> bool:  # pragma: no cover - mirror redis API
        return True

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value
        self._ttl[key] = ex

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self._store.pop(key, None)
            self._ttl.pop(key, None)

    async def scan_iter(self, match: str) -> AsyncIterator[str]:
        for key in list(self._store.keys()):
            if fnmatch.fnmatch(key, match):
                yield key

    async def aclose(self) -> None:  # pragma: no cover - compatibility shim
        self._store.clear()
        self._ttl.clear()


def test_cache_client_round_trip() -> None:
    """CacheClient should round-trip JSON payloads and honour TTL settings."""

    async def _scenario() -> None:
        fake_redis = InMemoryRedis()
        cache = CacheClient(fake_redis)

        await cache.set_json("demo", {"value": 42}, ttl=120)
        raw_payload = fake_redis._store["demo"]
        assert json.loads(raw_payload) == {"value": 42}
        assert fake_redis._ttl["demo"] == 120

        cached = await cache.get_json("demo")
        assert cached == {"value": 42}

        await cache.delete("demo")
        assert await cache.get_json("demo") is None

    asyncio.run(_scenario())


def test_delete_pattern_clears_matching_keys() -> None:
    async def _scenario() -> None:
        fake_redis = InMemoryRedis()
        cache = CacheClient(fake_redis)

        await cache.set_json("events:list:completed:20:0", {"value": 1})
        await cache.set_json("events:list:completed:20:20", {"value": 2})
        await cache.set_json("fighters:list:20:0", {"value": 3})

        await cache.delete_pattern("events:list:*")

        assert await cache.get_json("events:list:completed:20:0") is None
        assert await cache.get_json("events:list:completed:20:20") is None
        assert await cache.get_json("fighters:list:20:0") == {"value": 3}

    asyncio.run(_scenario())


def test_key_builders_normalize_input() -> None:
    """Key helper utilities should normalise text and hash signatures."""

    assert detail_key("abc") == "fighters:detail:abc"
    assert list_key(25, 10) == "fighters:list:25:10"

    search_digest = search_key(
        "  Jon Jones  ", "Orthodox", division=None, limit=10, offset=0
    )
    assert search_digest.startswith("fighters:search:")

    cmp_key = comparison_key(["id-1", "id-2"])
    assert cmp_key.startswith("fighters:compare:")

    graph_digest = graph_key(
        division="Lightweight",
        start_year=2010,
        end_year=2020,
        limit=25,
        include_upcoming=True,
    )
    assert graph_digest.startswith("fighters:graph:")

    assert event_detail_key("456") == "events:detail:456"

    list_key_value = event_list_key(status="Upcoming", limit=20, offset=40)
    assert list_key_value == "events:list:upcoming:20:40"

    search_key_value = event_search_key(
        query=" UFC 300 ",
        year=2024,
        location="Las Vegas",
        event_type="PPV",
        status="Completed",
        limit=20,
        offset=0,
    )
    assert search_key_value.startswith("events:search:")

    related_key = related_events_key(location="Las Vegas", limit=5)
    assert related_key.endswith(":5")
