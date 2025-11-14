from __future__ import annotations

import asyncio
import sys
import types
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock

import pytest


class _FakeRedis:  # pragma: no cover - lightweight shim for import-time wiring
    """Minimal asyncio-compatible Redis stand-in for service import paths."""

    @classmethod
    def from_url(cls, *args: object, **kwargs: object) -> _FakeRedis:
        """Return a new stub client regardless of configuration inputs."""

        return cls()

    async def ping(self) -> None:
        return None

    async def get(self, key: str) -> None:  # noqa: D401 - intentionally returns None
        """Always behave like an empty cache."""

        return None

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        return None

    async def delete(self, *keys: str) -> None:
        return None

    async def scan_iter(self, match: str | None = None):  # type: ignore[override]
        # This method is intentionally an async generator that yields nothing,
        # to satisfy interface requirements for test stubs.
        return
        yield  # unreachable, but marks this as an async generator

    async def aclose(self) -> None:
        return None


_redis_module = types.ModuleType("redis")
_redis_asyncio_module = types.ModuleType("redis.asyncio")
_redis_asyncio_module.Redis = _FakeRedis
_redis_exceptions_module = types.ModuleType("redis.exceptions")


class _FakeConnectionError(Exception):
    """Stub exception mirroring ``redis.exceptions.ConnectionError``."""


_redis_exceptions_module.ConnectionError = _FakeConnectionError

sys.modules.setdefault("redis", _redis_module)
sys.modules["redis.asyncio"] = _redis_asyncio_module
sys.modules["redis.exceptions"] = _redis_exceptions_module

try:
    from sqlalchemy.ext.asyncio import (  # type: ignore[attr-defined]
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    pytest.skip(
        f"Optional dependency '{exc.name}' is required for event repository tests.",
        allow_module_level=True,
    )

try:
    import aiosqlite  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard
    pytest.skip(
        "Optional dependency 'aiosqlite' is required for event repository tests.",
        allow_module_level=True,
    )

# Import backend modules after dependency stubs are registered to avoid optional import errors.
from backend.db.models import Base, Event, Fight, Fighter  # noqa: E402
from backend.db.repositories import PostgreSQLEventRepository  # noqa: E402
from backend.schemas.event import EventListItem, PaginatedEventsResponse  # noqa: E402
from backend.services.event_service import EventService  # noqa: E402


@asynccontextmanager
async def session_ctx() -> AsyncIterator[AsyncSession]:
    """Async context manager yielding an in-memory SQLite session."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        try:
            yield session
        finally:
            if session.in_transaction():
                await session.rollback()

    await engine.dispose()


def test_get_event_includes_weight_class() -> None:
    """Stored bout weight classes should surface through event fight payloads."""

    async def runner() -> None:
        async with session_ctx() as session:
            event = Event(
                id="evt-1",
                name="UFC Test Night",
                date=date(2024, 1, 1),
                location="Testville",
                status="completed",
                venue="Test Arena",
                broadcast="Test Network",
                promotion="UFC",
                ufcstats_url="https://www.ufcstats.com/event-details/evt-1",
                tapology_url="https://www.tapology.com/events/evt-1",
                sherdog_url="https://www.sherdog.com/events/evt-1",
            )
            fighter = Fighter(id="fighter-1", name="Test Fighter")
            fight = Fight(
                id="fight-1",
                fighter_id=fighter.id,
                event_id=event.id,
                opponent_id="fighter-2",
                opponent_name="Opponent One",
                event_name=event.name,
                event_date=event.date,
                result="win",
                method="KO",
                round=1,
                time="0:30",
                fight_card_url="https://www.ufcstats.com/fight-details/fight-1",
                weight_class="Lightweight",
            )

            session.add_all([event, fighter, fight])
            await session.flush()

            repository = PostgreSQLEventRepository(session)

            detail = await repository.get_event(event.id)
            assert detail is not None
            assert detail.fight_card, "Expected at least one fight in the fight card"
            assert detail.fight_card[0].weight_class == "Lightweight"

    asyncio.run(runner())


def test_get_event_with_missing_weight_class() -> None:
    """Events lacking stored weight classes should expose ``None`` for the field."""

    async def runner() -> None:
        async with session_ctx() as session:
            event = Event(
                id="evt-2",
                name="UFC Mystery Night",
                date=date(2024, 2, 2),
                location="Mystery City",
                status="completed",
                venue="Mystery Arena",
                broadcast="Mystery Network",
                promotion="UFC",
                ufcstats_url="https://www.ufcstats.com/event-details/evt-2",
                tapology_url=None,
                sherdog_url=None,
            )
            fighter = Fighter(id="fighter-3", name="Another Fighter")
            fight = Fight(
                id="fight-2",
                fighter_id=fighter.id,
                event_id=event.id,
                opponent_id=None,
                opponent_name="Unknown Opponent",
                event_name=event.name,
                event_date=event.date,
                result="loss",
                method="Decision",
                round=3,
                time="5:00",
                fight_card_url="https://www.ufcstats.com/fight-details/fight-2",
                weight_class=None,
            )

            session.add_all([event, fighter, fight])
            await session.flush()

            repository = PostgreSQLEventRepository(session)

            detail = await repository.get_event(event.id)
            assert detail is not None
            assert detail.fight_card, "Expected at least one fight in the fight card"
            assert detail.fight_card[0].weight_class is None

    asyncio.run(runner())


def test_search_events_filters_event_type_with_manual_pagination() -> None:
    """Ensure event-type filtering paginates after in-memory classification."""

    async def runner() -> None:
        async with session_ctx() as session:
            events: list[Event] = [
                Event(
                    id="evt-a",
                    name="UFC Fight Night: Alpha",
                    date=date(2024, 3, 1),
                    location="Test City",
                    status="completed",
                ),
                Event(
                    id="evt-b",
                    name="UFC Fight Night: Beta",
                    date=date(2024, 4, 1),
                    location="Test City",
                    status="completed",
                ),
                Event(
                    id="evt-c",
                    name="UFC Fight Night: Gamma",
                    date=date(2024, 5, 1),
                    location="Test City",
                    status="completed",
                ),
                Event(
                    id="evt-d",
                    name="UFC 300: Example",
                    date=date(2024, 6, 1),
                    location="Another City",
                    status="completed",
                ),
                Event(
                    id="evt-e",
                    name="Dana White's Contender Series 50",
                    date=date(2024, 7, 1),
                    location="Another City",
                    status="completed",
                ),
            ]

            session.add_all(events)
            await session.flush()

            repository = PostgreSQLEventRepository(session)
            service = EventService(repository)

            # Page one should contain the two most recent fight night cards.
            first_page: PaginatedEventsResponse = await service.search_events(
                event_type="fight_night",
                limit=2,
                offset=0,
            )
            assert [event.event_id for event in first_page.events] == ["evt-c", "evt-b"]
            assert len(first_page.events) == 2
            assert first_page.has_more is True

            # Page two should surface the remaining fight night entry with no more pages.
            second_page: PaginatedEventsResponse = await service.search_events(
                event_type="fight_night",
                limit=2,
                offset=2,
            )
            assert [event.event_id for event in second_page.events] == ["evt-a"]
            assert len(second_page.events) == 1
            assert second_page.has_more is False
            assert first_page.total == 3
            assert second_page.total == 3

    asyncio.run(runner())


def test_count_search_events_applies_filters() -> None:
    """The count helper should honour each search filter server-side."""

    async def runner() -> None:
        async with session_ctx() as session:
            events = [
                Event(
                    id="evt-1",
                    name="UFC Fight Night: Alpha",
                    date=date(2024, 3, 1),
                    location="Metropolis",
                    status="completed",
                ),
                Event(
                    id="evt-2",
                    name="UFC 300: Example",
                    date=date(2024, 4, 1),
                    location="Metropolis",
                    status="completed",
                ),
                Event(
                    id="evt-3",
                    name="Dana White's Contender Series 50",
                    date=date(2023, 9, 1),
                    location="Las Vegas",
                    status="upcoming",
                ),
            ]

            session.add_all(events)
            await session.flush()

            repository = PostgreSQLEventRepository(session)

            total_completed = await repository.count_search_events(status="completed")
            assert total_completed == 2

            total_fight_night = await repository.count_search_events(
                event_type="fight_night", status="completed"
            )
            assert total_fight_night == 1

            total_filtered = await repository.count_search_events(
                q="Alpha",
                year=2024,
                location="Metro",
                event_type="fight_night",
                status="completed",
            )
            assert total_filtered == 1

            total_upcoming = await repository.count_search_events(status="upcoming")
            assert total_upcoming == 1

    asyncio.run(runner())


def test_event_service_search_events_uses_count_helper() -> None:
    """Service search should rely on the repository count helper exactly once."""

    async def runner() -> None:
        repository = AsyncMock(spec=PostgreSQLEventRepository)
        repository.search_events.return_value = [
            EventListItem(
                event_id="evt-1",
                name="UFC Fight Night: Alpha",
                date=date(2024, 3, 1),
                location="Metropolis",
                status="completed",
                venue=None,
                broadcast=None,
                event_type="fight_night",
            )
        ]
        repository.count_search_events.return_value = 5

        service = EventService(repository)

        response = await service.search_events(
            q="Alpha",
            year=2024,
            location="Metro",
            event_type="fight_night",
            status="completed",
            limit=1,
            offset=0,
        )

        repository.search_events.assert_awaited_once_with(
            q="Alpha",
            year=2024,
            location="Metro",
            event_type="fight_night",
            status="completed",
            limit=1,
            offset=0,
        )
        repository.count_search_events.assert_awaited_once_with(
            q="Alpha",
            year=2024,
            location="Metro",
            event_type="fight_night",
            status="completed",
        )

        assert response.total == 5
        assert response.events[0].event_id == "evt-1"

    asyncio.run(runner())
