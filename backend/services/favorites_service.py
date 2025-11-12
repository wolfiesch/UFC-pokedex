"""Business logic powering the favorites API endpoints.

Persistence-oriented operations delegated to :class:`FavoritesPersistence`:
* ``tables_ready`` – readiness probe ensuring tables exist before use.
* ``list_collections`` – primary query used by ``list_collections`` handler.
* ``load_collection`` – shared loader for single-collection workflows.
* ``create_collection``/``update_collection``/``delete_collection`` – CRUD helpers.
* ``add_entry``/``update_entry``/``delete_entry``/``reorder_entries`` – entry
  mutation helpers that maintain positional integrity.
* ``fetch_fights_for_entries`` – supporting query for analytics calculations.

Analytics responsibilities handled by :class:`FavoritesAnalytics`:
* ``compute_collection_stats`` – aggregation powering stats cards.
* ``entries_to_schema``/``entry_to_schema`` – presentation layer conversions.
* ``build_activity`` – audit trail derived from entry timestamps.
* ``collection_summary`` and ``collection_detail`` – schema builders consumed by
  the API layer.

Separating concerns keeps :class:`FavoritesService` focused on coordinating the
workflow while making each collaborator individually testable.
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import CacheClient, get_cache_client
from backend.db.connection import get_db
from backend.db.models import FavoriteCollection, FavoriteEntry as FavoriteEntryModel
from backend.schemas.favorites import (
    FavoriteCollectionCreate,
    FavoriteCollectionDetail,
    FavoriteCollectionListResponse,
    FavoriteCollectionStats,
    FavoriteCollectionSummary,
    FavoriteCollectionUpdate,
    FavoriteEntryCreate,
    FavoriteEntryReorderRequest,
    FavoriteEntryUpdate,
)
from backend.schemas.favorites import (
    FavoriteEntry as FavoriteEntrySchema,
)
from backend.services.favorites import (
    FavoritesAnalytics,
    FavoritesCache,
    FavoritesPersistence,
)


class FavoritesService:
    """Orchestrates persistence, analytics, and caching dependencies."""

    def __init__(
        self,
        *,
        persistence: FavoritesPersistence,
        analytics: FavoritesAnalytics,
        cache: FavoritesCache,
    ) -> None:
        self._persistence = persistence
        self._analytics = analytics
        self._cache = cache

    async def list_collections(self, *, user_id: str) -> FavoriteCollectionListResponse:
        if not await self._persistence.tables_ready():
            return FavoriteCollectionListResponse(total=0, collections=[])

        cached = await self._cache.read_collection_list(user_id=user_id)
        if cached is not None:
            return cached

        collections = await self._persistence.list_collections(user_id=user_id)
        summaries: list[FavoriteCollectionSummary] = []
        for collection in collections:
            stats = await self._get_collection_stats(collection)
            summaries.append(
                self._analytics.collection_summary(collection, stats=stats)
            )

        payload = FavoriteCollectionListResponse(
            total=len(summaries),
            collections=summaries,
        )
        await self._cache.write_collection_list(user_id=user_id, payload=payload)
        return payload

    async def get_collection(
        self, *, collection_id: int, user_id: str | None = None
    ) -> FavoriteCollectionDetail | None:
        if not await self._persistence.tables_ready():
            return None

        cached = await self._cache.read_collection_detail(collection_id=collection_id)
        if cached is not None:
            if user_id is not None and cached.user_id != user_id:
                return None
            return cached

        collection = await self._persistence.load_collection(collection_id)
        if collection is None:
            return None
        if user_id is not None and collection.user_id != user_id:
            return None

        return await self._build_collection_detail(collection)

    async def create_collection(
        self, payload: FavoriteCollectionCreate
    ) -> FavoriteCollectionDetail:
        if not await self._persistence.tables_ready():
            raise RuntimeError(
                "Favorites tables are missing; run database migrations to enable favorites."
            )

        collection = await self._persistence.create_collection(payload)
        await self._cache.invalidate(user_id=collection.user_id)
        return await self._build_collection_detail(collection)

    async def update_collection(
        self,
        *,
        collection_id: int,
        user_id: str | None,
        payload: FavoriteCollectionUpdate,
    ) -> FavoriteCollectionDetail:
        if not await self._persistence.tables_ready():
            raise RuntimeError(
                "Favorites tables are missing; run database migrations to enable favorites."
            )

        collection = await self._persistence.load_collection(collection_id)
        if collection is None:
            raise LookupError("Collection not found")
        if user_id is not None and collection.user_id != user_id:
            raise PermissionError("Collection does not belong to the supplied user")

        await self._persistence.update_collection(collection, payload)
        await self._cache.invalidate(
            collection_id=collection.id, user_id=collection.user_id
        )
        return await self._build_collection_detail(collection)

    async def delete_collection(
        self, *, collection_id: int, user_id: str | None
    ) -> None:
        if not await self._persistence.tables_ready():
            return

        collection = await self._persistence.load_collection(collection_id)
        if collection is None:
            return
        if user_id is not None and collection.user_id != user_id:
            raise PermissionError("Collection does not belong to the supplied user")

        await self._persistence.delete_collection(collection)
        await self._cache.invalidate(
            collection_id=collection.id, user_id=collection.user_id
        )

    async def add_entry(
        self,
        *,
        collection_id: int,
        user_id: str | None,
        payload: FavoriteEntryCreate,
    ) -> FavoriteEntrySchema:
        if not await self._persistence.tables_ready():
            raise RuntimeError(
                "Favorites tables are missing; run database migrations to enable favorites."
            )

        collection = await self._require_collection(collection_id, user_id)
        entry = await self._persistence.add_entry(collection, payload)
        await self._cache.invalidate(
            collection_id=collection.id, user_id=collection.user_id
        )
        return self._analytics.entry_to_schema(entry)

    async def update_entry(
        self,
        *,
        collection_id: int,
        entry_id: int,
        user_id: str | None,
        payload: FavoriteEntryUpdate,
    ) -> FavoriteEntrySchema:
        if not await self._persistence.tables_ready():
            raise RuntimeError(
                "Favorites tables are missing; run database migrations to enable favorites."
            )

        collection = await self._require_collection(collection_id, user_id)
        entry = self._require_entry(collection, entry_id)
        await self._persistence.update_entry(collection, entry, payload)
        await self._cache.invalidate(
            collection_id=collection.id, user_id=collection.user_id
        )
        return self._analytics.entry_to_schema(entry)

    async def delete_entry(
        self,
        *,
        collection_id: int,
        entry_id: int,
        user_id: str | None,
    ) -> None:
        if not await self._persistence.tables_ready():
            return

        collection = await self._persistence.load_collection(collection_id)
        if collection is None:
            return
        if user_id is not None and collection.user_id != user_id:
            raise PermissionError("Collection does not belong to the supplied user")

        await self._persistence.ensure_entries_loaded(collection)
        entry = next((item for item in collection.entries if item.id == entry_id), None)
        if entry is None:
            return

        await self._persistence.delete_entry(collection, entry)
        await self._cache.invalidate(
            collection_id=collection.id, user_id=collection.user_id
        )

    async def reorder_entries(
        self,
        *,
        collection_id: int,
        user_id: str | None,
        payload: FavoriteEntryReorderRequest,
    ) -> FavoriteCollectionDetail:
        if not await self._persistence.tables_ready():
            raise RuntimeError(
                "Favorites tables are missing; run database migrations to enable favorites."
            )

        collection = await self._require_collection(collection_id, user_id)
        await self._persistence.reorder_entries(collection, payload)
        await self._cache.invalidate(
            collection_id=collection.id, user_id=collection.user_id
        )
        return await self._build_collection_detail(collection)

    async def _build_collection_detail(
        self, collection: FavoriteCollection
    ) -> FavoriteCollectionDetail:
        await self._persistence.ensure_entries_loaded(collection)
        stats = await self._get_collection_stats(collection)
        entries = self._analytics.entries_to_schema(collection.entries)
        activity = self._analytics.build_activity(collection.entries)
        detail = self._analytics.collection_detail(
            collection,
            stats=stats,
            entries=entries,
            activity=activity,
        )
        await self._cache.write_collection_detail(
            collection_id=collection.id, payload=detail
        )
        return detail

    async def _get_collection_stats(
        self, collection: FavoriteCollection
    ) -> FavoriteCollectionStats:
        cached = await self._cache.read_collection_stats(collection_id=collection.id)
        if cached is not None:
            return cached

        await self._persistence.ensure_entries_loaded(collection)
        fights = await self._persistence.fetch_fights_for_entries(collection)
        stats = self._analytics.compute_collection_stats(
            entries=collection.entries,
            fights=fights,
        )
        await self._cache.write_collection_stats(
            collection_id=collection.id, payload=stats
        )
        return stats

    async def _require_collection(
        self, collection_id: int, user_id: str | None
    ) -> FavoriteCollection:
        collection = await self._persistence.load_collection(collection_id)
        if collection is None:
            raise LookupError("Collection not found")
        if user_id is not None and collection.user_id != user_id:
            raise PermissionError("Collection does not belong to the supplied user")
        await self._persistence.ensure_entries_loaded(collection)
        return collection

    def _require_entry(
        self, collection: FavoriteCollection, entry_id: int
    ) -> FavoriteEntryModel:
        entry = next((item for item in collection.entries if item.id == entry_id), None)
        if entry is None:
            raise LookupError("Entry not found")
        return entry


async def get_favorites_service(
    session: AsyncSession = Depends(get_db),
    cache_client: CacheClient = Depends(get_cache_client),
) -> FavoritesService:
    """FastAPI dependency that wires the orchestrator together."""

    persistence = FavoritesPersistence(session)
    analytics = FavoritesAnalytics()
    cache = FavoritesCache(cache_client)
    return FavoritesService(
        persistence=persistence,
        analytics=analytics,
        cache=cache,
    )
