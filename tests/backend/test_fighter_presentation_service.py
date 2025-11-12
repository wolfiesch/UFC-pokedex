from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime as dt_datetime, timezone

import pytest

try:
    import pytest_asyncio
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    pytest.skip(
        f"Optional dependency '{exc.name}' is required for fighter presentation tests.",
        allow_module_level=True,
    )

from backend.db.models import Base, Fight, Fighter
from backend.db.repositories.fighter_repository import FighterRepository
from backend.services.fighter_presentation_service import FighterPresentationService


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Yield an in-memory SQLite session for mapper exercises."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        if session.in_transaction():
            await session.rollback()

    await engine.dispose()


def freeze_service_datetime(
    monkeypatch: pytest.MonkeyPatch, *, reference_date: date
) -> None:
    """Freeze ``datetime.now`` in the presentation service for deterministic ages."""

    class FrozenDateTime(dt_datetime):
        """Minimal datetime shim returning ``reference_date`` in UTC."""

        @classmethod
        def now(cls, tz: timezone | None = None) -> dt_datetime:  # type: ignore[override]
            reference_moment: dt_datetime = dt_datetime(
                reference_date.year,
                reference_date.month,
                reference_date.day,
                tzinfo=UTC,
            )
            return reference_moment if tz is None else reference_moment.astimezone(tz)

    monkeypatch.setattr(
        "backend.services.fighter_presentation_service.datetime", FrozenDateTime
    )


@pytest.mark.asyncio
async def test_list_fighters_computes_age(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """List items should surface ages derived from date of birth."""

    freeze_service_datetime(monkeypatch, reference_date=date(2024, 6, 16))

    fighter = Fighter(id="mapper-age", name="Mapper Age", dob=date(1994, 6, 15))
    session.add(fighter)
    await session.flush()

    repository = FighterRepository(session)
    presentation = FighterPresentationService(repository)

    listings = await presentation.list_fighters()
    assert listings[0].fighter_id == "mapper-age"
    assert listings[0].age == 30


@pytest.mark.asyncio
async def test_get_fighter_builds_fight_history(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Detail payloads should combine primary and opponent fight rows."""

    freeze_service_datetime(monkeypatch, reference_date=date(2024, 1, 1))

    primary = Fighter(id="primary", name="Primary")
    opponent = Fighter(id="opponent", name="Opponent")
    session.add_all([primary, opponent])
    await session.flush()

    primary_fight = Fight(
        id="fight-1",
        fighter_id="primary",
        opponent_id="opponent",
        opponent_name="Opponent",
        event_name="Event One",
        event_date=date(2023, 1, 1),
        result="win",
        method="KO",
        round=1,
        time="0:30",
        fight_card_url="http://example.com/fight-1",
    )

    opponent_fight = Fight(
        id="fight-2",
        fighter_id="opponent",
        opponent_id="primary",
        opponent_name="Primary",
        event_name="Event Two",
        event_date=date(2022, 6, 1),
        result="loss",
        method="Submission",
        round=2,
        time="1:10",
        fight_card_url="http://example.com/fight-2",
    )

    session.add_all([primary_fight, opponent_fight])
    await session.flush()

    repository = FighterRepository(session)
    presentation = FighterPresentationService(repository)

    detail = await presentation.get_fighter("primary")
    assert detail is not None
    # Ensure opponent perspective fight was inverted and deduplicated
    assert len(detail.fight_history) == 2
    results = {entry.event_name: entry.result for entry in detail.fight_history}
    assert results["Event One"].lower() == "win"
    assert results["Event Two"].lower() == "win"
