from __future__ import annotations

import asyncio
import json
import os
from hashlib import sha256
from typing import Any, Sequence

from redis.asyncio import Redis

_DEFAULT_TTL_SECONDS = 600
_DETAIL_PREFIX = "fighters:detail"
_LIST_PREFIX = "fighters:list"
_SEARCH_PREFIX = "fighters:search"
_COMPARISON_PREFIX = "fighters:compare"

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
    limit: int | None = None,
    offset: int | None = None,
) -> str:
    parts = [
        query.strip().lower(),
        (stance or "").strip().lower(),
        str(limit) if limit is not None else "",
        str(offset) if offset is not None else "",
    ]
    digest = sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"{_SEARCH_PREFIX}:{digest}"


def comparison_key(fighter_ids: Sequence[str]) -> str:
    ordered = sorted(fighter_ids)
    signature = "|".join(ordered)
    digest = sha256(signature.encode("utf-8")).hexdigest()
    return f"{_COMPARISON_PREFIX}:{digest}:{signature}"


async def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        async with _client_lock:
            if _redis_client is None:
                _redis_client = Redis.from_url(
                    _redis_url(), decode_responses=True, encoding="utf-8"
                )
    return _redis_client


class CacheClient:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get_json(self, key: str) -> Any:
        payload = await self._redis.get(key)
        if payload is None:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        encoded = json.dumps(value, default=str)
        if ttl is None:
            ttl = _DEFAULT_TTL_SECONDS
        await self._redis.set(key, encoded, ex=ttl)

    async def delete(self, *keys: str) -> None:
        if keys:
            await self._redis.delete(*keys)

    async def delete_pattern(self, pattern: str) -> None:
        async for key in self._redis.scan_iter(match=pattern):
            await self._redis.delete(key)


async def get_cache_client() -> CacheClient:
    redis = await get_redis()
    return CacheClient(redis)


async def invalidate_fighter(cache: CacheClient, fighter_id: str) -> None:
    await cache.delete(detail_key(fighter_id))
    await cache.delete_pattern(f"{_COMPARISON_PREFIX}:*{fighter_id}*")


async def invalidate_collections(cache: CacheClient) -> None:
    await cache.delete_pattern(f"{_LIST_PREFIX}:*")
    await cache.delete_pattern(f"{_SEARCH_PREFIX}:*")


__all__ = [
    "CacheClient",
    "comparison_key",
    "detail_key",
    "get_cache_client",
    "invalidate_collections",
    "invalidate_fighter",
    "list_key",
    "search_key",
]
