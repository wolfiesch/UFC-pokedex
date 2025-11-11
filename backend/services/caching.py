"""Common caching utilities shared across service layers.

This module centralises the cache interaction logic that previously lived inside
``FighterService`` so that specialised services can focus purely on domain
behaviour.  The :func:`cached` decorator adds a thin asynchronous wrapper around
service methods, providing two-tier caching (Redis + in-process) with optional
serialisation hooks.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, Concatenate, ParamSpec, TypeVar, cast

from backend.cache import CacheClient

logger = logging.getLogger(__name__)

_LOCAL_CACHE_DEFAULT_TTL = 300
_local_cache: dict[str, tuple[float, Any]] = {}
_local_cache_lock = asyncio.Lock()

P = ParamSpec("P")
T = TypeVar("T")

CacheKeyBuilder = Callable[Concatenate["CacheableService", P], str | None]
CacheSerializer = Callable[[T], Any]
CacheDeserializer = Callable[[Any], T]
DecoratedCallable = Callable[Concatenate["CacheableService", P], Awaitable[T]]


async def _local_cache_get(key: str) -> Any | None:
    """Return a cached value from the in-process cache if still valid."""

    async with _local_cache_lock:
        entry = _local_cache.get(key)
        if entry is None:
            return None

        expires_at, value = entry
        if expires_at < time.time():
            _local_cache.pop(key, None)
            return None
        return value


async def _local_cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    """Store ``value`` in the in-process cache honouring an optional TTL."""

    ttl_seconds = ttl if ttl is not None and ttl > 0 else _LOCAL_CACHE_DEFAULT_TTL
    async with _local_cache_lock:
        _local_cache[key] = (time.time() + ttl_seconds, value)


class CacheableService:
    """Base class that exposes helper methods for two-tier caching.

    Services inheriting from this mixin gain access to ``_cache_get`` and
    ``_cache_set`` methods which first consult any configured distributed cache
    before falling back to an in-process dictionary.  The mixin purposefully has
    a tiny surface so that it can be composed with repository-focused services
    without complicating their inheritance chains.
    """

    def __init__(self, cache: CacheClient | None = None) -> None:
        self._cache = cache

    async def _cache_get(self, key: str) -> Any:
        """Fetch a cached value from Redis (if configured) or the local cache."""

        cached: Any | None = None
        if self._cache is not None:
            cached = await self._cache.get_json(key)
        if cached is not None:
            return cached
        return await _local_cache_get(key)

    async def _cache_set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Persist a cached value to Redis (if configured) and the local cache."""

        if self._cache is not None:
            await self._cache.set_json(key, value, ttl=ttl)
        if value is not None:
            await _local_cache_set(key, value, ttl=ttl)


def cached(
    key_builder: CacheKeyBuilder[P],
    *,
    ttl: int | None = None,
    serializer: CacheSerializer[T] | None = None,
    deserializer: CacheDeserializer[T] | None = None,
    deserialize_error_message: str | None = None,
) -> Callable[[DecoratedCallable], DecoratedCallable]:
    """Decorate an async service method with transparent caching behaviour.

    Parameters
    ----------
    key_builder:
        Callable that returns the cache key for the invocation.  Returning
        ``None`` short-circuits caching for the call.
    ttl:
        Optional cache lifetime in seconds.  ``None`` falls back to the default
        TTL defined for the in-process cache.
    serializer / deserializer:
        Optional hooks that convert between Python objects and JSON-serialisable
        payloads.  They are invoked before writing to the cache and after
        reading from it respectively.
    deserialize_error_message:
        Optional ``str.format`` template used for logging if the cached payload
        cannot be deserialised.
    """

    def decorator(func: DecoratedCallable) -> DecoratedCallable:
        @wraps(func)
        async def wrapper(
            self: "CacheableService", *args: P.args, **kwargs: P.kwargs
        ) -> T:
            cache_key = key_builder(self, *args, **kwargs)
            if cache_key:
                cached_value = await self._cache_get(cache_key)
                if cached_value is not None:
                    if deserializer is not None:
                        try:
                            return deserializer(cached_value)
                        except Exception as exc:  # pragma: no cover - defensive logging
                            if deserialize_error_message:
                                logger.warning(
                                    deserialize_error_message.format(
                                        key=cache_key, error=exc
                                    )
                                )
                    else:
                        return cast(T, cached_value)

            result = await func(self, *args, **kwargs)

            if cache_key and result is not None:
                payload: Any = result
                if serializer is not None:
                    payload = serializer(result)
                try:
                    await self._cache_set(cache_key, payload, ttl=ttl)
                except Exception as exc:  # pragma: no cover - cache backend issues
                    logger.warning(
                        "Failed to persist cache entry for key %s: %s", cache_key, exc
                    )

            return result

        return wrapper

    return decorator


__all__ = ["CacheableService", "cached"]
