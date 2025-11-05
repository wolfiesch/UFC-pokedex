"""Business logic powering the favorites API endpoints."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Iterable

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.cache import (
    CacheClient,
    favorite_collection_key,
    favorite_list_key,
    favorite_stats_key,
    get_cache_client,
)
from backend.db.connection import get_db
from backend.db.models import (
    FavoriteCollection,
    FavoriteEntry as FavoriteEntryModel,
    Fight,
    Fighter,
)
from backend.schemas.favorites import (
    FavoriteActivityItem,
    FavoriteCollectionCreate,
    FavoriteCollectionDetail,
    FavoriteCollectionListResponse,
    FavoriteCollectionStats,
    FavoriteCollectionSummary,
    FavoriteCollectionUpdate,
    FavoriteEntry as FavoriteEntrySchema,
    FavoriteEntryCreate,
    FavoriteEntryReorderRequest,
    FavoriteEntryUpdate,
    FavoriteUpcomingFight,
)


class FavoritesService:
    """Encapsulates persistence, caching, and aggregation for favorites."""

    def __init__(self, session: AsyncSession, cache: CacheClient) -> None:
        self._session = session
        self._cache = cache

    async def list_collections(self, *, user_id: str) -> FavoriteCollectionListResponse:
        cache_key = favorite_list_key(user_id)
        cached = await self._cache.get_json(cache_key)
        if cached is not None:
            summaries = [
                FavoriteCollectionSummary(**item)
                for item in cached.get("collections", [])
            ]
            return FavoriteCollectionListResponse(
                total=cached.get("total", len(summaries)),
                collections=summaries,
            )

        query = (
            select(FavoriteCollection)
            .options(
                selectinload(FavoriteCollection.entries).selectinload(
                    FavoriteEntryModel.fighter
                )
            )
            .where(FavoriteCollection.user_id == user_id)
            .order_by(FavoriteCollection.created_at.desc())
        )
        result = await self._session.execute(query)
        collections = result.scalars().unique().all()

        summaries: list[FavoriteCollectionSummary] = []
        for collection in collections:
            stats = await self._get_collection_stats(collection)
            summaries.append(self._collection_to_summary(collection, stats=stats))

        payload = FavoriteCollectionListResponse(
            total=len(summaries),
            collections=summaries,
        )
        await self._cache.set_json(cache_key, payload.model_dump(mode="json"))
        return payload

    async def get_collection(
        self, *, collection_id: int, user_id: str | None = None
    ) -> FavoriteCollectionDetail | None:
        cache_key = favorite_collection_key(collection_id)
        cached = await self._cache.get_json(cache_key)
        if cached is not None:
            detail = FavoriteCollectionDetail(**cached)
            if user_id is not None and detail.user_id != user_id:
                return None
            return detail

        collection = await self._load_collection(collection_id)
        if collection is None:
            return None
        if user_id is not None and collection.user_id != user_id:
            return None

        detail = await self._collection_to_detail(collection)
        await self._cache.set_json(cache_key, detail.model_dump(mode="json"))
        return detail

    async def create_collection(
        self, payload: FavoriteCollectionCreate
    ) -> FavoriteCollectionDetail:
        collection = FavoriteCollection(
            user_id=payload.user_id,
            title=payload.title,
            slug=payload.slug,
            description=payload.description,
            is_public=payload.is_public,
            metadata_json=payload.metadata,
        )
        self._session.add(collection)
        await self._session.flush()
        await self._invalidate_cache(user_id=collection.user_id)
        return await self._collection_to_detail(collection)

    async def update_collection(
        self,
        *,
        collection_id: int,
        user_id: str | None,
        payload: FavoriteCollectionUpdate,
    ) -> FavoriteCollectionDetail:
        collection = await self._load_collection(collection_id)
        if collection is None:
            raise LookupError("Collection not found")
        if user_id is not None and collection.user_id != user_id:
            raise PermissionError("Collection does not belong to the supplied user")

        if payload.title is not None:
            collection.title = payload.title
        if payload.description is not None:
            collection.description = payload.description
        if payload.is_public is not None:
            collection.is_public = payload.is_public
        if payload.slug is not None:
            collection.slug = payload.slug
        if payload.metadata is not None:
            collection.metadata_json = payload.metadata
        collection.updated_at = datetime.now(timezone.utc)

        await self._session.flush()
        await self._invalidate_cache(
            collection_id=collection.id, user_id=collection.user_id
        )
        return await self._collection_to_detail(collection)

    async def delete_collection(
        self, *, collection_id: int, user_id: str | None
    ) -> None:
        collection = await self._load_collection(collection_id)
        if collection is None:
            return
        if user_id is not None and collection.user_id != user_id:
            raise PermissionError("Collection does not belong to the supplied user")

        await self._session.delete(collection)
        await self._session.flush()
        await self._invalidate_cache(
            collection_id=collection.id, user_id=collection.user_id
        )

    async def add_entry(
        self,
        *,
        collection_id: int,
        user_id: str | None,
        payload: FavoriteEntryCreate,
    ) -> FavoriteEntrySchema:
        collection = await self._load_collection(collection_id)
        if collection is None:
            raise LookupError("Collection not found")
        if user_id is not None and collection.user_id != user_id:
            raise PermissionError("Collection does not belong to the supplied user")

        existing = next(
            (
                entry
                for entry in collection.entries
                if entry.fighter_id == payload.fighter_id
            ),
            None,
        )
        if existing is not None:
            raise ValueError("Fighter already exists in the collection")

        position = payload.position
        if position >= len(collection.entries):
            position = len(collection.entries)

        entry = FavoriteEntryModel(
            collection_id=collection.id,
            fighter_id=payload.fighter_id,
            position=position,
            notes=payload.notes,
            tags=payload.tags,
            metadata_json=payload.metadata,
        )
        self._session.add(entry)
        collection.entries.append(entry)

        await self._session.flush()
        await self._normalize_positions(collection)
        await self._session.flush()
        await self._invalidate_cache(
            collection_id=collection.id, user_id=collection.user_id
        )
        return self._entry_to_schema(entry)

    async def update_entry(
        self,
        *,
        collection_id: int,
        entry_id: int,
        user_id: str | None,
        payload: FavoriteEntryUpdate,
    ) -> FavoriteEntrySchema:
        collection = await self._load_collection(collection_id)
        if collection is None:
            raise LookupError("Collection not found")
        if user_id is not None and collection.user_id != user_id:
            raise PermissionError("Collection does not belong to the supplied user")

        entry = next((item for item in collection.entries if item.id == entry_id), None)
        if entry is None:
            raise LookupError("Entry not found")

        if payload.position is not None:
            entry.position = payload.position
        if payload.notes is not None:
            entry.notes = payload.notes
        if payload.tags is not None:
            entry.tags = payload.tags
        if payload.metadata is not None:
            entry.metadata_json = payload.metadata
        entry.updated_at = datetime.now(timezone.utc)

        await self._normalize_positions(collection)
        await self._session.flush()
        await self._invalidate_cache(
            collection_id=collection.id, user_id=collection.user_id
        )
        return self._entry_to_schema(entry)

    async def delete_entry(
        self,
        *,
        collection_id: int,
        entry_id: int,
        user_id: str | None,
    ) -> None:
        collection = await self._load_collection(collection_id)
        if collection is None:
            return
        if user_id is not None and collection.user_id != user_id:
            raise PermissionError("Collection does not belong to the supplied user")

        entry = next((item for item in collection.entries if item.id == entry_id), None)
        if entry is None:
            return

        await self._session.delete(entry)
        await self._session.flush()
        await self._normalize_positions(collection)
        await self._session.flush()
        await self._invalidate_cache(
            collection_id=collection.id, user_id=collection.user_id
        )

    async def reorder_entries(
        self,
        *,
        collection_id: int,
        user_id: str | None,
        payload: FavoriteEntryReorderRequest,
    ) -> FavoriteCollectionDetail:
        collection = await self._load_collection(collection_id)
        if collection is None:
            raise LookupError("Collection not found")
        if user_id is not None and collection.user_id != user_id:
            raise PermissionError("Collection does not belong to the supplied user")

        lookup = {entry.id: entry for entry in collection.entries}
        if set(lookup.keys()) != set(payload.entry_ids):
            raise ValueError("Reorder payload must reference every entry exactly once")

        for index, entry_id in enumerate(payload.entry_ids):
            lookup[entry_id].position = index

        await self._session.flush()
        await self._invalidate_cache(
            collection_id=collection.id, user_id=collection.user_id
        )
        return await self._collection_to_detail(collection)

    async def _load_collection(self, collection_id: int) -> FavoriteCollection | None:
        query = (
            select(FavoriteCollection)
            .options(
                selectinload(FavoriteCollection.entries).selectinload(
                    FavoriteEntryModel.fighter
                )
            )
            .where(FavoriteCollection.id == collection_id)
        )
        result = await self._session.execute(query)
        return result.scalars().unique().one_or_none()

    def _collection_to_summary(
        self,
        collection: FavoriteCollection,
        *,
        stats: FavoriteCollectionStats | None,
    ) -> FavoriteCollectionSummary:
        return FavoriteCollectionSummary(
            id=collection.id,
            user_id=collection.user_id,
            title=collection.title,
            description=collection.description,
            is_public=collection.is_public,
            slug=collection.slug,
            metadata=collection.metadata_json or {},
            created_at=collection.created_at,
            updated_at=collection.updated_at,
            stats=stats,
        )

    async def _collection_to_detail(
        self, collection: FavoriteCollection
    ) -> FavoriteCollectionDetail:
        stats = await self._get_collection_stats(collection)
        entries = sorted(collection.entries, key=lambda entry: entry.position)
        entry_payload = [self._entry_to_schema(entry) for entry in entries]
        activity = self._build_activity(entries)
        detail = FavoriteCollectionDetail(
            id=collection.id,
            user_id=collection.user_id,
            title=collection.title,
            description=collection.description,
            is_public=collection.is_public,
            slug=collection.slug,
            metadata=collection.metadata_json or {},
            created_at=collection.created_at,
            updated_at=collection.updated_at,
            stats=stats,
            entries=entry_payload,
            activity=activity,
        )
        cache_key = favorite_collection_key(collection.id)
        await self._cache.set_json(cache_key, detail.model_dump(mode="json"))
        return detail

    async def _get_collection_stats(
        self, collection: FavoriteCollection
    ) -> FavoriteCollectionStats:
        cache_key = favorite_stats_key(collection.id)
        cached = await self._cache.get_json(cache_key)
        if cached is not None:
            return FavoriteCollectionStats(**cached)

        stats = await self._compute_collection_stats(collection)
        await self._cache.set_json(cache_key, stats.model_dump(mode="json"))
        return stats

    async def _compute_collection_stats(
        self, collection: FavoriteCollection
    ) -> FavoriteCollectionStats:
        if not collection.entries:
            return FavoriteCollectionStats(
                total_fighters=0,
                win_rate=0.0,
                result_breakdown=self._empty_breakdown(),
                divisions=[],
                upcoming_fights=[],
            )

        fighter_ids = [entry.fighter_id for entry in collection.entries]
        query = select(Fight).where(Fight.fighter_id.in_(fighter_ids))
        result = await self._session.execute(query)
        fights = result.scalars().all()

        breakdown = Counter(self._normalize_result(fight.result) for fight in fights)
        normalized = self._empty_breakdown()
        normalized.update(breakdown)

        wins = normalized.get("win", 0)
        losses = normalized.get("loss", 0)
        win_rate = wins / (wins + losses) if (wins + losses) else 0.0

        divisions = sorted(
            {
                entry.fighter.division
                for entry in collection.entries
                if isinstance(entry.fighter, Fighter) and entry.fighter.division
            }
        )

        upcoming = [
            FavoriteUpcomingFight(
                fighter_id=fight.fighter_id,
                opponent_name=fight.opponent_name,
                event_name=fight.event_name,
                event_date=fight.event_date,
                weight_class=fight.weight_class,
            )
            for fight in fights
            if self._normalize_result(fight.result) == "upcoming"
        ]

        return FavoriteCollectionStats(
            total_fighters=len(collection.entries),
            win_rate=win_rate,
            result_breakdown=normalized,
            divisions=divisions,
            upcoming_fights=upcoming,
        )

    def _entry_to_schema(self, entry: FavoriteEntryModel) -> FavoriteEntrySchema:
        return FavoriteEntrySchema(
            id=entry.id,
            fighter_id=entry.fighter_id,
            position=entry.position,
            notes=entry.notes,
            tags=list(entry.tags or []),
            metadata=entry.metadata_json or {},
            created_at=entry.added_at,
            updated_at=entry.updated_at,
        )

    def _build_activity(
        self, entries: Iterable[FavoriteEntryModel]
    ) -> list[FavoriteActivityItem]:
        feed: list[FavoriteActivityItem] = []
        for entry in sorted(entries, key=lambda item: item.updated_at, reverse=True):
            action = (
                "updated"
                if entry.updated_at and entry.updated_at > entry.added_at
                else "added"
            )
            metadata: dict[str, object] = {}
            if entry.notes:
                metadata["notes"] = entry.notes
            if entry.tags:
                metadata["tags"] = entry.tags
            feed.append(
                FavoriteActivityItem(
                    entry_id=entry.id,
                    fighter_id=entry.fighter_id,
                    action=action,
                    occurred_at=(
                        entry.updated_at if action == "updated" else entry.added_at
                    ),
                    metadata=metadata,
                )
            )
        return feed

    async def _normalize_positions(self, collection: FavoriteCollection) -> None:
        entries = sorted(collection.entries, key=lambda entry: entry.position)
        for index, entry in enumerate(entries):
            entry.position = index

    async def _invalidate_cache(
        self,
        *,
        collection_id: int | None = None,
        user_id: str | None = None,
    ) -> None:
        keys: list[str] = []
        if collection_id is not None:
            keys.append(favorite_collection_key(collection_id))
            keys.append(favorite_stats_key(collection_id))
        if user_id is not None:
            keys.append(favorite_list_key(user_id))
        if keys:
            await self._cache.delete(*keys)

    def _empty_breakdown(self) -> dict[str, int]:
        """
        Returns a template dictionary for fight result categories with zero counts.
        Ensures all expected keys are present in the breakdown dictionary.
        """
        return {"win": 0, "loss": 0, "draw": 0, "nc": 0, "upcoming": 0, "other": 0}

    def _normalize_result(self, result: str | None) -> str:
        if result is None:
            return "other"
        normalized = result.strip().lower()
        if normalized in {"w", "win"}:
            return "win"
        if normalized in {"l", "loss"}:
            return "loss"
        if normalized.startswith("draw"):
            return "draw"
        if normalized in {"nc", "no contest"}:
            return "nc"
        if normalized == "next":
            return "upcoming"
        return "other"


async def get_favorites_service(
    session: AsyncSession = Depends(get_db),
    cache: CacheClient = Depends(get_cache_client),
) -> FavoritesService:
    return FavoritesService(session, cache)
