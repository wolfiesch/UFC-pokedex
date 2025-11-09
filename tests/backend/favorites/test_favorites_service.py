"""Unit tests for the favorites service aggregation and caching logic."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest

try:
    import pytest_asyncio
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy.orm import Session
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    pytest.skip(
        f"Optional dependency '{exc.name}' is required for favorites service tests.",
        allow_module_level=True,
    )

from backend.cache import favorite_collection_key, favorite_list_key, favorite_stats_key
from backend.db.models import (
    Base,
    Fight,
    Fighter,
    FavoriteCollection,
    FavoriteEntry as FavoriteEntryModel,
)
from backend.schemas.favorites import (
    FavoriteCollectionCreate,
    FavoriteEntryCreate,
    FavoriteEntryReorderRequest,
)
import backend.services.favorites_service as favorites_module


class MemoryCache:
    """In-memory cache double that mimics :class:`backend.cache.CacheClient`."""

    def __init__(self) -> None:
        self.store: dict[str, object] = {}
        self.deleted: list[str] = []

    async def get_json(self, key: str) -> object | None:
        return self.store.get(key)

    async def set_json(self, key: str, value: object, ttl: int | None = None) -> None:
        self.store[key] = value

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self.store.pop(key, None)
            self.deleted.append(key)

    async def delete_pattern(
        self, pattern: str
    ) -> None:  # pragma: no cover - unused shim
        keys_to_delete = [
            key for key in self.store if key.startswith(pattern.rstrip("*"))
        ]
        for key in keys_to_delete:
            await self.delete(key)


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Yield an in-memory SQLite session with freshly created tables."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        if session.in_transaction():
            await session.rollback()
    await engine.dispose()


@pytest.fixture(autouse=True)
def reset_favorites_tables_cache() -> Iterator[None]:
    """Ensure the process-wide favorites readiness cache starts fresh for each test."""

    previous_cache: bool | None = favorites_module._FAVORITES_TABLES_READY_CACHE
    favorites_module._FAVORITES_TABLES_READY_CACHE = None
    yield
    favorites_module._FAVORITES_TABLES_READY_CACHE = previous_cache


@pytest.mark.asyncio
async def test_stats_aggregation_populates_cache(session: AsyncSession) -> None:
    """Stats should capture win rate, divisions, and upcoming fights."""

    lightweight = Fighter(id="fighter-a", name="Alpha", division="Lightweight")
    welterweight = Fighter(id="fighter-b", name="Bravo", division="Welterweight")
    session.add_all([lightweight, welterweight])
    await session.flush()

    session.add_all(
        [
            Fight(
                id="fight-1",
                fighter_id="fighter-a",
                opponent_id="fighter-x",
                opponent_name="Opponent X",
                event_id=None,
                event_name="UFC 300",
                event_date=None,
                result="Win",
                method=None,
                round=None,
                time=None,
                fight_card_url=None,
                stats={},
                weight_class="Lightweight",
            ),
            Fight(
                id="fight-2",
                fighter_id="fighter-a",
                opponent_id="fighter-y",
                opponent_name="Opponent Y",
                event_id=None,
                event_name="UFC 301",
                event_date=None,
                result="Next",
                method=None,
                round=None,
                time=None,
                fight_card_url=None,
                stats={},
                weight_class="Lightweight",
            ),
            Fight(
                id="fight-3",
                fighter_id="fighter-b",
                opponent_id="fighter-z",
                opponent_name="Opponent Z",
                event_id=None,
                event_name="UFC 302",
                event_date=None,
                result="Loss",
                method=None,
                round=None,
                time=None,
                fight_card_url=None,
                stats={},
                weight_class="Welterweight",
            ),
        ]
    )
    await session.flush()

    cache = MemoryCache()
    service = FavoritesService(session, cache)

    detail = await service.create_collection(
        FavoriteCollectionCreate(
            user_id="tester",
            title="Watchlist",
            description="Follow these fighters",
            is_public=False,
            slug="watchlist",
            metadata={},
        )
    )

    await service.add_entry(
        collection_id=detail.id,
        user_id="tester",
        payload=FavoriteEntryCreate(
            fighter_id="fighter-a",
            position=0,
            notes="Primary prospect",
            tags=["prospect"],
            metadata={},
        ),
    )
    await service.add_entry(
        collection_id=detail.id,
        user_id="tester",
        payload=FavoriteEntryCreate(
            fighter_id="fighter-b",
            position=1,
            notes="Needs more tape",
            tags=["review"],
            metadata={},
        ),
    )

    hydrated = await service.get_collection(collection_id=detail.id, user_id="tester")
    assert hydrated is not None
    assert hydrated.stats is not None
    stats = hydrated.stats
    assert stats.total_fighters == 2
    assert pytest.approx(stats.win_rate, rel=1e-6) == 0.5
    assert stats.result_breakdown["win"] == 1
    assert stats.result_breakdown["loss"] == 1
    assert stats.result_breakdown["upcoming"] == 1
    assert set(stats.divisions) == {"Lightweight", "Welterweight"}
    assert len(stats.upcoming_fights) == 1
    assert stats.upcoming_fights[0].event_name == "UFC 301"

    # Ensure stats and detail were written to cache for future hits.
    assert favorite_collection_key(detail.id) in cache.store
    assert favorite_stats_key(detail.id) in cache.store

    # Second retrieval should be served from cache without altering stats.
    cached = await service.get_collection(collection_id=detail.id, user_id="tester")
    assert cached is not None
    assert cached.stats == stats


@pytest.mark.asyncio
async def test_tables_ready_cache_recovers_after_initial_failure(
    session: AsyncSession,
) -> None:
    """FavoritesService should recover once the tables appear after an initial miss."""

    def _drop_tables(sync_session: Session) -> None:
        """Remove favorites tables to mimic an environment where migrations lag."""

        FavoriteEntryModel.__table__.drop(sync_session.connection(), checkfirst=True)
        FavoriteCollection.__table__.drop(sync_session.connection(), checkfirst=True)

    def _create_tables(sync_session: Session) -> None:
        """Recreate favorites tables after the simulated migration completes."""

        FavoriteCollection.__table__.create(sync_session.connection(), checkfirst=True)
        FavoriteEntryModel.__table__.create(sync_session.connection(), checkfirst=True)

    await session.run_sync(_drop_tables)

    cache = MemoryCache()
    service = FavoritesService(session, cache)

    response = await service.list_collections(user_id="tester")
    assert response.total == 0
    assert service._tables_ready is False
    assert favorites_module._FAVORITES_TABLES_READY_CACHE is None

    await session.run_sync(_create_tables)

    created = await service.create_collection(
        FavoriteCollectionCreate(
            user_id="tester",
            title="Active",
            description="Newly available after migrations.",
            is_public=False,
            slug="active",
            metadata={},
        )
    )

    assert created.id is not None
    assert service._tables_ready is True
    assert favorites_module._FAVORITES_TABLES_READY_CACHE is True

    refreshed = await service.list_collections(user_id="tester")
    assert refreshed.total == 1
    assert refreshed.collections[0].id == created.id


@pytest.mark.asyncio
async def test_reorder_entries_resets_positions_and_expires_listing_cache(
    session: AsyncSession,
) -> None:
    """Reordering entries should resequence positions and invalidate list cache."""

    session.add_all(
        [
            Fighter(id="fighter-1", name="One"),
            Fighter(id="fighter-2", name="Two"),
            Fighter(id="fighter-3", name="Three"),
        ]
    )
    await session.flush()

    cache = MemoryCache()
    service = FavoritesService(session, cache)

    detail = await service.create_collection(
        FavoriteCollectionCreate(
            user_id="owner",
            title="Camp",
            description=None,
            is_public=True,
            slug="camp",
            metadata={},
        )
    )

    for index, fighter_id in enumerate(["fighter-1", "fighter-2", "fighter-3"]):
        await service.add_entry(
            collection_id=detail.id,
            user_id="owner",
            payload=FavoriteEntryCreate(
                fighter_id=fighter_id,
                position=index,
                notes=None,
                tags=[],
                metadata={},
            ),
        )

    current = await service.get_collection(collection_id=detail.id, user_id="owner")
    assert current is not None
    original_ids = [entry.id for entry in current.entries]
    reversed_ids = list(reversed(original_ids))

    # Warm the list cache so we can assert it gets invalidated by reorder.
    await service.list_collections(user_id="owner")
    list_key = favorite_list_key("owner")
    assert list_key in cache.store

    reordered = await service.reorder_entries(
        collection_id=detail.id,
        user_id="owner",
        payload=FavoriteEntryReorderRequest(entry_ids=reversed_ids),
    )

    # Positions should now be normalized to 0..N-1 regardless of payload ordering.
    assert [entry.position for entry in reordered.entries] == [0, 1, 2]
    assert {entry.fighter_id for entry in reordered.entries} == {
        "fighter-3",
        "fighter-2",
        "fighter-1",
    }

    # The detail and stats cache should be refreshed, while the list cache is removed.
    assert list_key not in cache.store
    assert favorite_collection_key(detail.id) in cache.store
    assert favorite_stats_key(detail.id) in cache.store
