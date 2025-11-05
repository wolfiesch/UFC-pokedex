from __future__ import annotations

import asyncio
import json
import logging
import os
from hashlib import sha256
from typing import Any, Sequence

from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

logger = logging.getLogger(__name__)

_DEFAULT_TTL_SECONDS = 600
_DETAIL_PREFIX = "fighters:detail"
_LIST_PREFIX = "fighters:list"
_SEARCH_PREFIX = "fighters:search"
_COMPARISON_PREFIX = "fighters:compare"
_GRAPH_PREFIX = "fighters:graph"
_EVENT_LIST_PREFIX = "events:list"
_EVENT_DETAIL_PREFIX = "events:detail"
_EVENT_SEARCH_PREFIX = "events:search"
_EVENT_RELATED_PREFIX = "events:related"

_redis_client: Redis | None = None
_client_lock = asyncio.Lock()


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def detail_key(fighter_id: str) -> str:
    return f"{_DETAIL_PREFIX}:{fighter_id}"


def list_key(limit: int, offset: int) -> str:
    return f"{_LIST_PREFIX}:{limit}:{offset}"


def search_key(
    query: str,
    stance: str | None,
    division: str | None = None,
    champion_statuses: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> str:
    parts = [
        query.strip().lower(),
        (stance or "").strip().lower(),
        (division or "").strip().lower(),
        (champion_statuses or "").strip().lower(),
        str(limit) if limit is not None else "",
        str(offset) if offset is not None else "",
    ]
    digest = sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"{_SEARCH_PREFIX}:{digest}"


def comparison_key(fighter_ids: Sequence[str]) -> str:
    signature = "|".join(fighter_ids)
    digest = sha256(signature.encode("utf-8")).hexdigest()
    return f"{_COMPARISON_PREFIX}:{digest}:{signature}"


def graph_key(
    *,
    division: str | None,
    start_year: int | None,
    end_year: int | None,
    limit: int | None,
    include_upcoming: bool,
) -> str:
    parts = [
        (division or "").strip().lower(),
        str(start_year) if start_year is not None else "",
        str(end_year) if end_year is not None else "",
        str(limit) if limit is not None else "",
        "1" if include_upcoming else "0",
    ]
    digest = sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"{_GRAPH_PREFIX}:{digest}"


def event_list_key(*, status: str | None, limit: int | None, offset: int | None) -> str:
    """Build a cache key for event list queries.

    The ``status`` flag differentiates upcoming versus completed payloads while the
    pagination arguments ensure distinct cache entries for each page. The function
    lowercases the status because callers may pass human-entered values.
    """

    normalized_status = (status or "all").strip().lower()
    return f"{_EVENT_LIST_PREFIX}:{normalized_status}:{limit}:{offset}"


def event_detail_key(event_id: str) -> str:
    """Produce a stable cache key for an event detail lookup."""

    return f"{_EVENT_DETAIL_PREFIX}:{event_id}"


def event_search_key(
    *,
    query: str | None,
    year: int | None,
    location: str | None,
    event_type: str | None,
    status: str | None,
    limit: int,
    offset: int,
) -> str:
    """Create a hash-based cache key for advanced event search queries.

    We combine all filters into a signature and hash the string to avoid excessively
    long Redis keys when the ``query`` or ``location`` inputs are verbose.
    """

    parts = [
        (query or "").strip().lower(),
        str(year) if year is not None else "",
        (location or "").strip().lower(),
        (event_type or "").strip().lower(),
        (status or "").strip().lower(),
        str(limit),
        str(offset),
    ]
    digest = sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"{_EVENT_SEARCH_PREFIX}:{digest}"


def related_events_key(*, location: str, limit: int) -> str:
    """Return a cache key for related events lookups scoped by location."""

    normalized_location = location.strip().lower()
    digest = sha256(normalized_location.encode("utf-8")).hexdigest()
    return f"{_EVENT_RELATED_PREFIX}:{digest}:{limit}"


async def get_redis() -> Redis | None:
    """Get Redis client, returning None if connection fails."""
    global _redis_client
    if _redis_client is None:
        async with _client_lock:
            if _redis_client is None:
                try:
                    _redis_client = Redis.from_url(
                        _redis_url(), decode_responses=True, encoding="utf-8"
                    )
                    # Test connection
                    await _redis_client.ping()
                    logger.info("Redis connection established successfully")
                except (RedisConnectionError, Exception) as e:
                    logger.warning(
                        f"Redis connection failed: {e}. Caching will be disabled."
                    )
                    _redis_client = None
    return _redis_client


class CacheClient:
    def __init__(self, redis: Redis | None) -> None:
        self._redis = redis

    async def get_json(self, key: str) -> Any:
        if self._redis is None:
            return None
        try:
            payload = await self._redis.get(key)
            if payload is None:
                return None
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                return None
        except (RedisConnectionError, Exception) as e:
            logger.debug(f"Redis get failed for key {key}: {e}")
            return None

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        if self._redis is None:
            return
        try:
            encoded = json.dumps(value, default=str)
            if ttl is None:
                ttl = _DEFAULT_TTL_SECONDS
            await self._redis.set(key, encoded, ex=ttl)
        except (RedisConnectionError, Exception) as e:
            logger.debug(f"Redis set failed for key {key}: {e}")

    async def delete(self, *keys: str) -> None:
        if self._redis is None or not keys:
            return
        try:
            await self._redis.delete(*keys)
        except (RedisConnectionError, Exception) as e:
            logger.debug(f"Redis delete failed: {e}")

    async def delete_pattern(self, pattern: str) -> None:
        if self._redis is None:
            return
        try:
            async for key in self._redis.scan_iter(match=pattern):
                await self._redis.delete(key)
        except (RedisConnectionError, Exception) as e:
            logger.debug(f"Redis delete_pattern failed for {pattern}: {e}")


async def get_cache_client() -> CacheClient:
    redis = await get_redis()
    return CacheClient(redis)


async def close_redis() -> None:
    """Close the global Redis connection gracefully."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


async def invalidate_fighter(cache: CacheClient, fighter_id: str) -> None:
    await cache.delete(detail_key(fighter_id))
    await cache.delete_pattern(f"{_COMPARISON_PREFIX}:*{fighter_id}*")


async def invalidate_collections(cache: CacheClient) -> None:
    await cache.delete_pattern(f"{_LIST_PREFIX}:*")
    await cache.delete_pattern(f"{_SEARCH_PREFIX}:*")


__all__ = [
    "CacheClient",
    "close_redis",
    "comparison_key",
    "graph_key",
    "detail_key",
    "get_cache_client",
    "invalidate_collections",
    "invalidate_fighter",
    "list_key",
    "search_key",
    "event_list_key",
    "event_detail_key",
    "event_search_key",
    "related_events_key",
]
