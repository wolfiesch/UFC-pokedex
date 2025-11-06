from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Sequence
from hashlib import sha256
from typing import TYPE_CHECKING, Any

try:
    from redis.asyncio import Redis
    from redis.exceptions import ConnectionError as RedisConnectionError
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Redis = None  # type: ignore[assignment]

    class RedisConnectionError(Exception):
        """Fallback exception class defined when redis package is not installed."""


if TYPE_CHECKING:
    from redis.asyncio import Redis as RedisClient
else:  # pragma: no cover - runtime fallback for optional dependency
    RedisClient = Any

logger = logging.getLogger(__name__)

_DEFAULT_TTL_SECONDS = 600
_DETAIL_PREFIX = "fighters:detail"
_LIST_PREFIX = "fighters:list"
_SEARCH_PREFIX = "fighters:search"
_COMPARISON_PREFIX = "fighters:compare"
_GRAPH_PREFIX = "fighters:graph"
_FAVORITE_LIST_PREFIX = "favorites:list"
_FAVORITE_COLLECTION_PREFIX = "favorites:collection"
_FAVORITE_STATS_PREFIX = "favorites:stats"

_redis_client: RedisClient | None = None
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
    streak_type: str | None = None,
    min_streak_count: int | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> str:
    parts = [
        query.strip().lower(),
        (stance or "").strip().lower(),
        (division or "").strip().lower(),
        (champion_statuses or "").strip().lower(),
        (streak_type or "").strip().lower(),
        str(min_streak_count) if min_streak_count is not None else "",
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


def favorite_list_key(user_id: str) -> str:
    return f"{_FAVORITE_LIST_PREFIX}:{user_id}"


def favorite_collection_key(collection_id: int | str) -> str:
    return f"{_FAVORITE_COLLECTION_PREFIX}:{collection_id}"


def favorite_stats_key(collection_id: int | str) -> str:
    return f"{_FAVORITE_STATS_PREFIX}:{collection_id}"


async def get_redis() -> RedisClient | None:
    """Get Redis client, returning None if connection fails."""
    global _redis_client
    if Redis is None:
        logger.info("Redis dependency not installed; caching remains disabled.")
        return None

    # ALWAYS acquire lock first to prevent TOCTOU race
    async with _client_lock:
        # Double-check pattern inside lock
        if _redis_client is not None:
            return _redis_client

        try:
            _redis_client = Redis.from_url(
                _redis_url(), decode_responses=True, encoding="utf-8"
            )
            # Test connection
            await _redis_client.ping()
            logger.info("Redis connection established successfully")
            return _redis_client
        except RedisConnectionError as e:
            logger.warning(
                f"Redis connection failed: {e}. Caching will be disabled."
            )
            return None


class CacheClient:
    def __init__(self, redis: RedisClient | None) -> None:
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
        except RedisConnectionError as e:
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
        except RedisConnectionError as e:
            logger.debug(f"Redis set failed for key {key}: {e}")

    async def delete(self, *keys: str) -> None:
        if self._redis is None or not keys:
            return
        try:
            await self._redis.delete(*keys)
        except RedisConnectionError as e:
            logger.debug(f"Redis delete failed: {e}")

    async def delete_pattern(self, pattern: str) -> None:
        if self._redis is None:
            return
        try:
            async for key in self._redis.scan_iter(match=pattern):
                await self._redis.delete(key)
        except RedisConnectionError as e:
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
    """Invalidate all caches related to a fighter."""
    await cache.delete(detail_key(fighter_id))
    await cache.delete_pattern(f"{_COMPARISON_PREFIX}:*{fighter_id}*")

    # Also invalidate search and list caches (fighter data changed)
    await cache.delete_pattern(f"{_SEARCH_PREFIX}:*")
    await cache.delete_pattern(f"{_LIST_PREFIX}:*")

    # Invalidate count cache
    await cache.delete("fighters:count")


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
]
