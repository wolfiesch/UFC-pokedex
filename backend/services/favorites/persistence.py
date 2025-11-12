"""Database-oriented helpers for favorites collections."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from backend.db.models import (
    FavoriteCollection,
    FavoriteEntry as FavoriteEntryModel,
    Fight,
    Fighter,
)
from backend.schemas.favorites import (
    FavoriteCollectionCreate,
    FavoriteCollectionUpdate,
    FavoriteEntryCreate,
    FavoriteEntryReorderRequest,
    FavoriteEntryUpdate,
)

_FAVORITES_TABLES_READY_CACHE: bool | None = None


class FavoritesPersistence:
    """Encapsulates SQLAlchemy operations required by the favorites domain."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tables_ready: bool | None = None

    async def tables_ready(self) -> bool:
        """Check if the required tables exist, caching successes in-process."""

        global _FAVORITES_TABLES_READY_CACHE

        if _FAVORITES_TABLES_READY_CACHE is True:
            self._tables_ready = True
            return True

        if self._tables_ready is True:
            return True

        target_tables = {
            FavoriteCollection.__tablename__,
            FavoriteEntryModel.__tablename__,
        }

        def _check_tables(sync_session) -> bool:
            engine = sync_session.get_bind()
            if engine is None:
                return False

            inspector = inspect(engine)
            existing = set(inspector.get_table_names())
            return target_tables.issubset(existing)

        tables_ready = await self._session.run_sync(_check_tables)

        if tables_ready:
            self._tables_ready = True
            _FAVORITES_TABLES_READY_CACHE = True
        else:
            self._tables_ready = False

        return tables_ready

    async def list_collections(self, *, user_id: str) -> list[FavoriteCollection]:
        """Return collections with entries eagerly loaded for summary views."""

        entry_loader = selectinload(FavoriteCollection.entries).options(
            load_only(
                FavoriteEntryModel.id,
                FavoriteEntryModel.fighter_id,
                FavoriteEntryModel.position,
                FavoriteEntryModel.notes,
                FavoriteEntryModel.tags,
                FavoriteEntryModel.metadata_json,
                FavoriteEntryModel.added_at,
                FavoriteEntryModel.updated_at,
            ),
            selectinload(FavoriteEntryModel.fighter).options(
                load_only(Fighter.id, Fighter.division)
            ),
        )

        query = (
            select(FavoriteCollection)
            .options(entry_loader)
            .where(FavoriteCollection.user_id == user_id)
            .order_by(FavoriteCollection.created_at.desc())
        )
        result = await self._session.execute(query)
        return result.scalars().unique().all()

    async def load_collection(self, collection_id: int) -> FavoriteCollection | None:
        """Load a single collection with entries and fighter relationships."""

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

    async def create_collection(
        self, payload: FavoriteCollectionCreate
    ) -> FavoriteCollection:
        """Persist a new collection from the provided payload."""

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
        return collection

    async def update_collection(
        self, collection: FavoriteCollection, payload: FavoriteCollectionUpdate
    ) -> FavoriteCollection:
        """Apply updates to an existing collection."""

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
        collection.updated_at = datetime.now(UTC)

        await self._session.flush()
        return collection

    async def delete_collection(self, collection: FavoriteCollection) -> None:
        """Remove a collection from the database."""

        await self._session.delete(collection)
        await self._session.flush()

    async def add_entry(
        self, collection: FavoriteCollection, payload: FavoriteEntryCreate
    ) -> FavoriteEntryModel:
        """Create a new entry within a collection."""

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
        await self.normalize_positions(collection)
        await self._session.flush()
        return entry

    async def update_entry(
        self,
        collection: FavoriteCollection,
        entry: FavoriteEntryModel,
        payload: FavoriteEntryUpdate,
    ) -> FavoriteEntryModel:
        """Apply updates to an existing entry."""

        if payload.position is not None:
            entry.position = payload.position
        if payload.notes is not None:
            entry.notes = payload.notes
        if payload.tags is not None:
            entry.tags = payload.tags
        if payload.metadata is not None:
            entry.metadata_json = payload.metadata
        entry.updated_at = datetime.now(UTC)

        await self.normalize_positions(collection)
        await self._session.flush()
        return entry

    async def delete_entry(
        self, collection: FavoriteCollection, entry: FavoriteEntryModel
    ) -> None:
        """Delete an entry and normalize remaining positions."""

        await self._session.delete(entry)
        collection.entries.remove(entry)
        await self.normalize_positions(collection)
        await self._session.flush()

    async def reorder_entries(
        self,
        collection: FavoriteCollection,
        payload: FavoriteEntryReorderRequest,
    ) -> None:
        """Persist a new ordering for collection entries."""

        lookup = {entry.id: entry for entry in collection.entries}
        if set(lookup.keys()) != set(payload.entry_ids):
            raise ValueError("Reorder payload must reference every entry exactly once")

        for index, entry_id in enumerate(payload.entry_ids):
            lookup[entry_id].position = index

        await self._session.flush()

    async def ensure_entries_loaded(self, collection: FavoriteCollection) -> None:
        """Force-load entries to avoid async lazy loading issues."""

        await self._session.refresh(collection, ["entries"])

    async def fetch_fights_for_entries(
        self, collection: FavoriteCollection
    ) -> list[Fight]:
        """Fetch fights associated with the fighters in the collection."""

        fighter_ids = [entry.fighter_id for entry in collection.entries]
        if not fighter_ids:
            return []
        query = select(Fight).where(Fight.fighter_id.in_(fighter_ids))
        result = await self._session.execute(query)
        return result.scalars().all()

    async def normalize_positions(self, collection: FavoriteCollection) -> None:
        """Ensure positions are contiguous after mutations."""

        entries = sorted(collection.entries, key=lambda entry: entry.position)
        for index, entry in enumerate(entries):
            entry.position = index
