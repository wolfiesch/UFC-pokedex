from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections.abc import Sequence
from functools import lru_cache
from hashlib import sha256
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from redis.asyncio import Redis as RedisClient
    from redis.exceptions import ConnectionError as RedisConnectionError
else:  # pragma: no cover - runtime fallback for optional dependency
    try:
        from redis.asyncio import Redis as RedisClient  # type: ignore
        from redis.exceptions import ConnectionError as RedisConnectionError
    except ModuleNotFoundError:

        class RedisConnectionError(Exception):
            """Fallback exception class defined when redis package is not installed."""

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

_LOCAL_CACHE_DEFAULT_TTL = 300
_local_cache: dict[str, tuple[float, Any]] = {}
_local_cache_lock = asyncio.Lock()

_redis_client: RedisClient | None = None
_client_lock = asyncio.Lock()
_redis_disabled = False


async def local_cache_get(key: str) -> Any | None:
    """Return a value from the in-process fallback cache when it remains valid."""

    async with _local_cache_lock:
        cached_entry = _local_cache.get(key)
        if cached_entry is None:
            return None

        expires_at, value = cached_entry
        if expires_at < time.time():
            _local_cache.pop(key, None)
            return None
        return value


async def local_cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    """Persist ``value`` in the in-process cache while respecting the supplied TTL."""

    ttl_seconds = ttl if ttl is not None and ttl > 0 else _LOCAL_CACHE_DEFAULT_TTL
    async with _local_cache_lock:
        _local_cache[key] = (time.time() + ttl_seconds, value)


async def local_cache_evict(
    *,
    keys: Sequence[str] | None = None,
    prefixes: Sequence[str] | None = None,
    prefix_substring_filters: dict[str, Sequence[str]] | None = None,
) -> None:
    """Remove cached entries that match explicit keys or prefixed filters.

    Parameters
    ----------
    keys:
        Explicit cache keys that should be removed unconditionally.
    prefixes:
        Cache key prefixes whose entire namespaces should be purged.
    prefix_substring_filters:
        Mapping of cache key prefixes to substrings that must also appear within the key
        for the entry to be evicted. This is useful for comparison caches where fighter
        identifiers are embedded in the key signature.
    """

    async with _local_cache_lock:
        if keys:
            for exact_key in keys:
                _local_cache.pop(exact_key, None)

        if prefixes:
            matching_keys = [
                existing_key
                for existing_key in _local_cache
                if any(existing_key.startswith(prefix) for prefix in prefixes)
            ]
            for matching_key in matching_keys:
                _local_cache.pop(matching_key, None)

        if prefix_substring_filters:
            for prefix, substrings in prefix_substring_filters.items():
                if not substrings:
                    continue
                matching_keys = [
                    existing_key
                    for existing_key in _local_cache
                    if existing_key.startswith(prefix)
                    and any(substring in existing_key for substring in substrings)
                ]
                for matching_key in matching_keys:
                    _local_cache.pop(matching_key, None)


async def local_cache_clear_all() -> None:
    """Remove every entry from the in-process cache.

    This helper is primarily intended for test isolation while still being available to
    callers that need to aggressively reset the fallback cache state.
    """

    async with _local_cache_lock:
        _local_cache.clear()


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def detail_key(fighter_id: str) -> str:
    return f"{_DETAIL_PREFIX}:{fighter_id}"


def list_key(
    limit: int,
    offset: int,
    *,
    include_streak: bool = False,
    streak_window: int | None = None,
) -> str:
    streak_part = "1" if include_streak else "0"
    window_part = str(streak_window) if include_streak and streak_window is not None else ""
    return f"{_LIST_PREFIX}:{limit}:{offset}:{streak_part}:{window_part}"


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
    global _redis_client, _redis_disabled
    redis_class, _ = _load_redis_components()
    if redis_class is None:
        logger.info("Redis dependency not installed; caching remains disabled.")
        return None

    if _redis_disabled:
        logger.debug("Redis connection disabled after previous failure; skipping attempt.")
        return None

    # ALWAYS acquire lock first to prevent TOCTOU race
    async with _client_lock:
        # Double-check pattern inside lock
        if _redis_client is not None:
            return _redis_client

        if _redis_disabled:
            return None

        try:
            client: RedisClient = redis_class.from_url(  # type: ignore[call-arg]
                _redis_url(), decode_responses=True, encoding="utf-8"
            )
            # Test connection before storing the singleton instance.
            await client.ping()
            _redis_client = client
            logger.info("Redis connection established successfully")
            return _redis_client
        except Exception as exc:  # type: ignore[broad-except]
            if _is_redis_connection_error(exc):
                logger.warning(f"Redis connection failed: {exc}. Caching will be disabled.")
                _redis_client = None
                _redis_disabled = True
                return None
            raise


@lru_cache(maxsize=1)
def _load_redis_components() -> tuple[RedisClient | None, type[BaseException]]:
    """Return the Redis asyncio client class and connection error type."""

    try:  # pragma: no cover - optional dependency import
        from redis.asyncio import Redis as RedisClientType  # type: ignore
        from redis.exceptions import ConnectionError as RedisConnectionErrorType
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        return None, RedisConnectionError

    return RedisClientType, RedisConnectionErrorType


def _is_redis_connection_error(exc: BaseException) -> bool:
    """Return ``True`` when ``exc`` represents a Redis connection failure."""

    if isinstance(exc, RedisConnectionError):
        return True

    error_type = type(exc)
    return error_type.__name__ == "ConnectionError" and error_type.__module__.startswith("redis")


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
        except Exception as exc:  # type: ignore[broad-except]
            if _is_redis_connection_error(exc):
                logger.debug(f"Redis get failed for key {key}: {exc}")
                return None
            raise

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        if self._redis is None:
            return
        try:
            encoded = json.dumps(value, default=str)
            if ttl is None:
                ttl = _DEFAULT_TTL_SECONDS
            await self._redis.set(key, encoded, ex=ttl)
        except Exception as exc:  # type: ignore[broad-except]
            if _is_redis_connection_error(exc):
                logger.debug(f"Redis set failed for key {key}: {exc}")
                return
            raise

    async def delete(self, *keys: str) -> None:
        if self._redis is None or not keys:
            return
        try:
            await self._redis.delete(*keys)
        except Exception as exc:  # type: ignore[broad-except]
            if _is_redis_connection_error(exc):
                logger.debug(f"Redis delete failed: {exc}")
                return
            raise

    async def delete_pattern(self, pattern: str) -> None:
        if self._redis is None:
            return
        try:
            async for key in self._redis.scan_iter(match=pattern):
                await self._redis.delete(key)
        except Exception as exc:  # type: ignore[broad-except]
            if _is_redis_connection_error(exc):
                logger.debug(f"Redis delete_pattern failed for {pattern}: {exc}")
                return
            raise


async def get_cache_client() -> CacheClient:
    redis = await get_redis()
    return CacheClient(redis)


async def close_redis() -> None:
    """Close the global Redis connection gracefully."""
    global _redis_client, _redis_disabled
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
    _redis_disabled = False


async def invalidate_fighter(cache: CacheClient, fighter_id: str) -> None:
    """Invalidate all caches related to a fighter."""

    await cache.delete(detail_key(fighter_id))
    await cache.delete_pattern(f"{_COMPARISON_PREFIX}:*{fighter_id}*")

    # Ensure the local fallback cache mirrors the remote invalidation semantics.
    await local_cache_evict(
        keys=[detail_key(fighter_id), "fighters:count"],
        prefixes=[_LIST_PREFIX, _SEARCH_PREFIX],
        prefix_substring_filters={_COMPARISON_PREFIX: [fighter_id]},
    )

    # Also invalidate search and list caches (fighter data changed)
    await cache.delete_pattern(f"{_SEARCH_PREFIX}:*")
    await cache.delete_pattern(f"{_LIST_PREFIX}:*")

    # Invalidate count cache
    await cache.delete("fighters:count")


async def invalidate_collections(cache: CacheClient) -> None:
    await cache.delete_pattern(f"{_LIST_PREFIX}:*")
    await cache.delete_pattern(f"{_SEARCH_PREFIX}:*")
    await local_cache_evict(prefixes=[_LIST_PREFIX, _SEARCH_PREFIX])


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
    "local_cache_clear_all",
    "local_cache_evict",
    "local_cache_get",
    "local_cache_set",
    "search_key",
]
