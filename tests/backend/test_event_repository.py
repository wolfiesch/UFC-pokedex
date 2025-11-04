from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
import asyncio

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy.ext.asyncio import (  # type: ignore[attr-defined]
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.db.models import Base, Event, Fight, Fighter
from backend.db.repositories import PostgreSQLEventRepository


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
