"""Caching helpers dedicated to favorites orchestration."""

from __future__ import annotations

from typing import Iterable

from backend.cache import (
    CacheClient,
    favorite_collection_key,
    favorite_list_key,
    favorite_stats_key,
)
from backend.schemas.favorites import (
    FavoriteCollectionDetail,
    FavoriteCollectionListResponse,
    FavoriteCollectionStats,
    FavoriteCollectionSummary,
)


class FavoritesCache:
    """Wrap cache interactions for favorites payloads with documentation.

    The service only needs a handful of strongly typed helpers: list, detail,
    stats, and invalidation. Abstracting them behind this class keeps the
    orchestrator unaware of implementation details (Redis vs. in-memory) and
    guarantees that JSON encoding/decoding happens in a single place.
    """

    def __init__(self, client: CacheClient) -> None:
        self._client = client

    async def read_collection_list(
        self, *, user_id: str
    ) -> FavoriteCollectionListResponse | None:
        """Return a cached list response if present."""

        cache_key = favorite_list_key(user_id)
        cached = await self._client.get_json(cache_key)
        if cached is None:
            return None

        summaries = [
            FavoriteCollectionSummary(**item) for item in cached.get("collections", [])
        ]
        total = cached.get("total", len(summaries))
        return FavoriteCollectionListResponse(total=total, collections=summaries)

    async def write_collection_list(
        self,
        *,
        user_id: str,
        payload: FavoriteCollectionListResponse,
    ) -> None:
        """Persist a list payload."""

        cache_key = favorite_list_key(user_id)
        await self._client.set_json(cache_key, payload.model_dump(mode="json"))

    async def read_collection_detail(
        self, *, collection_id: int
    ) -> FavoriteCollectionDetail | None:
        """Return a cached detail payload if present."""

        cache_key = favorite_collection_key(collection_id)
        cached = await self._client.get_json(cache_key)
        return FavoriteCollectionDetail(**cached) if cached is not None else None

    async def write_collection_detail(
        self,
        *,
        collection_id: int,
        payload: FavoriteCollectionDetail,
    ) -> None:
        """Persist a detail payload."""

        cache_key = favorite_collection_key(collection_id)
        await self._client.set_json(cache_key, payload.model_dump(mode="json"))

    async def read_collection_stats(
        self, *, collection_id: int
    ) -> FavoriteCollectionStats | None:
        """Return cached statistics when available."""

        cache_key = favorite_stats_key(collection_id)
        cached = await self._client.get_json(cache_key)
        return FavoriteCollectionStats(**cached) if cached is not None else None

    async def write_collection_stats(
        self,
        *,
        collection_id: int,
        payload: FavoriteCollectionStats,
    ) -> None:
        """Persist computed statistics for subsequent lookups."""

        cache_key = favorite_stats_key(collection_id)
        await self._client.set_json(cache_key, payload.model_dump(mode="json"))

    async def invalidate(
        self,
        *,
        collection_id: int | None = None,
        user_id: str | None = None,
    ) -> None:
        """Delete any cached artifacts that may be stale."""

        keys: list[str] = []
        if collection_id is not None:
            keys.append(favorite_collection_key(collection_id))
            keys.append(favorite_stats_key(collection_id))
        if user_id is not None:
            keys.append(favorite_list_key(user_id))
        if keys:
            await self._client.delete(*keys)

    async def delete_many(self, keys: Iterable[str]) -> None:
        """Expose a typed delete helper for callers needing manual control."""

        await self._client.delete(*keys)
