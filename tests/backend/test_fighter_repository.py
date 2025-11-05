from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, date, timezone
from datetime import datetime as dt_datetime

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("pytest_asyncio")
pytest.importorskip("aiosqlite")

pytest_asyncio = pytest.importorskip("pytest_asyncio")
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.db.models import Base, Fighter
from backend.db.repositories import PostgreSQLFighterRepository


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Provide an in-memory SQLite session for repository exercises."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        if session.in_transaction():
            await session.rollback()

    await engine.dispose()


def freeze_utc_today(
    monkeypatch: pytest.MonkeyPatch,
    *,
    reference_date: date,
) -> None:
    """Freeze ``datetime.now`` inside the repository module to ``reference_date``.

    The production repository relies on ``datetime.now(tz=UTC)`` to compute a
    consistent "today" value.  Tests replace that call with a deterministic
    value so we can assert exact age calculations, including edge cases like
    leap-year birthdays or erroneous future dates.
    """

    class FrozenDateTime(dt_datetime):
        """Custom datetime shim returning the supplied reference moment."""

        @classmethod
        def now(cls, tz: timezone | None = None) -> dt_datetime:  # type: ignore[override]
            reference_moment: dt_datetime = dt_datetime(
                reference_date.year,
                reference_date.month,
                reference_date.day,
                tzinfo=UTC,
            )
            return reference_moment if tz is None else reference_moment.astimezone(tz)

    monkeypatch.setattr("backend.db.repositories.datetime", FrozenDateTime)


@pytest.mark.asyncio
async def test_list_fighters_orders_results_by_name_then_id(
    session: AsyncSession,
) -> None:
    alpha = Fighter(id="b-id", name="Alpha")
    bravo = Fighter(id="a-id", name="Bravo")
    charlie = Fighter(id="c-id", name="Charlie")
    session.add_all([alpha, bravo, charlie])
    await session.flush()

    repo = PostgreSQLFighterRepository(session)

    page_one = await repo.list_fighters(limit=2, offset=0)
    assert [fighter.name for fighter in page_one] == ["Alpha", "Bravo"]

    page_two = await repo.list_fighters(limit=2, offset=2)
    assert [fighter.name for fighter in page_two] == ["Charlie"]


@pytest.mark.asyncio
async def test_list_fighters_includes_age_field(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each list item should surface an age derived from the stored birth date."""

    freeze_utc_today(monkeypatch, reference_date=date(2024, 6, 16))

    fighter = Fighter(id="age-listing", name="List Age", dob=date(1990, 6, 15))
    session.add(fighter)
    await session.flush()

    repo = PostgreSQLFighterRepository(session)
    fighters = list(await repo.list_fighters())

    assert fighters[0].age == 34


@pytest.mark.asyncio
async def test_get_fighter_age_clamped_for_future_birthdays(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Future-dated birthdays should yield an age of zero rather than negatives."""

    freeze_utc_today(monkeypatch, reference_date=date(2024, 6, 16))

    fighter = Fighter(
        id="future-birthday",
        name="Temporal Glitch",
        dob=date(2025, 1, 1),
    )
    session.add(fighter)
    await session.commit()

    repo = PostgreSQLFighterRepository(session)
    detail = await repo.get_fighter("future-birthday")

    assert detail is not None
    assert detail.age == 0


@pytest.mark.asyncio
async def test_get_fighter_age_handles_leap_year_birthdays(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Leap-day birthdays should roll forward correctly on non-leap years."""

    freeze_utc_today(monkeypatch, reference_date=date(2025, 2, 28))

    fighter = Fighter(
        id="leap-birthday",
        name="Leap Day Legend",
        dob=date(2000, 2, 29),
    )
    session.add(fighter)
    await session.commit()

    repo = PostgreSQLFighterRepository(session)
    detail = await repo.get_fighter("leap-birthday")

    assert detail is not None
    assert detail.age == 24


@pytest.mark.asyncio
async def test_get_fighters_for_comparison_surfaces_age(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Comparison payloads should expose the computed age alongside other stats."""

    freeze_utc_today(monkeypatch, reference_date=date(2024, 6, 16))

    fighter = Fighter(
        id="comparison-age",
        name="Comparison Age",
        dob=date(1990, 6, 15),
    )
    session.add(fighter)
    await session.commit()

    repo = PostgreSQLFighterRepository(session)
    comparison = await repo.get_fighters_for_comparison(["comparison-age"])

    assert comparison and comparison[0].age == 34
