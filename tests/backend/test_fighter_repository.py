from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, date, timezone
from datetime import datetime as dt_datetime

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
        f"Optional dependency '{exc.name}' is required for fighter repository tests.",
        allow_module_level=True,
    )

try:
    import aiosqlite  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard
    pytest.skip(
        "Optional dependency 'aiosqlite' is required for fighter repository tests.",
        allow_module_level=True,
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

    monkeypatch.setattr(
        "backend.db.repositories.fighter.roster.datetime", FrozenDateTime
    )


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


@pytest.mark.asyncio
async def test_list_fighters_filters_by_nationality(
    session: AsyncSession,
) -> None:
    """Verify that nationality filter returns only fighters with matching nationality."""

    fighter_us = Fighter(
        id="us-fighter",
        name="American Fighter",
        nationality="American",
        last_fight_date=date(2024, 1, 1),
    )
    fighter_br = Fighter(
        id="br-fighter",
        name="Brazilian Fighter",
        nationality="Brazilian",
        last_fight_date=date(2024, 1, 2),
    )
    fighter_ie = Fighter(
        id="ie-fighter",
        name="Irish Fighter",
        nationality="Irish",
        last_fight_date=date(2024, 1, 3),
    )
    fighter_none = Fighter(
        id="none-fighter",
        name="Unknown Fighter",
        nationality=None,
        last_fight_date=date(2024, 1, 4),
    )

    session.add_all([fighter_us, fighter_br, fighter_ie, fighter_none])
    await session.flush()

    repo = PostgreSQLFighterRepository(session)

    # Test filtering by American nationality
    us_fighters = list(
        await repo.list_fighters(nationality="American", limit=10, offset=0)
    )
    assert len(us_fighters) == 1
    assert us_fighters[0].fighter_id == "us-fighter"
    assert us_fighters[0].nationality == "American"

    # Test filtering by Brazilian nationality
    br_fighters = list(
        await repo.list_fighters(nationality="Brazilian", limit=10, offset=0)
    )
    assert len(br_fighters) == 1
    assert br_fighters[0].fighter_id == "br-fighter"
    assert br_fighters[0].nationality == "Brazilian"

    # Test filtering by Irish nationality
    ie_fighters = list(
        await repo.list_fighters(nationality="Irish", limit=10, offset=0)
    )
    assert len(ie_fighters) == 1
    assert ie_fighters[0].fighter_id == "ie-fighter"
    assert ie_fighters[0].nationality == "Irish"

    # Test filtering by non-existent nationality
    jp_fighters = list(
        await repo.list_fighters(nationality="Japanese", limit=10, offset=0)
    )
    assert len(jp_fighters) == 0

    # Test no filter returns all fighters
    all_fighters = list(await repo.list_fighters(limit=10, offset=0))
    assert len(all_fighters) == 4


@pytest.mark.asyncio
async def test_count_fighters_filters_by_nationality(
    session: AsyncSession,
) -> None:
    """Verify that nationality filter in count_fighters returns correct counts."""

    fighter_us_1 = Fighter(
        id="us-fighter-1",
        name="American Fighter 1",
        nationality="American",
        last_fight_date=date(2024, 1, 1),
    )
    fighter_us_2 = Fighter(
        id="us-fighter-2",
        name="American Fighter 2",
        nationality="American",
        last_fight_date=date(2024, 1, 2),
    )
    fighter_br = Fighter(
        id="br-fighter",
        name="Brazilian Fighter",
        nationality="Brazilian",
        last_fight_date=date(2024, 1, 3),
    )
    fighter_ie = Fighter(
        id="ie-fighter",
        name="Irish Fighter",
        nationality="Irish",
        last_fight_date=date(2024, 1, 4),
    )
    fighter_none = Fighter(
        id="none-fighter",
        name="Unknown Fighter",
        nationality=None,
        last_fight_date=date(2024, 1, 5),
    )

    session.add_all([fighter_us_1, fighter_us_2, fighter_br, fighter_ie, fighter_none])
    await session.flush()

    repo = PostgreSQLFighterRepository(session)

    # Test count by American nationality
    us_count = await repo.count_fighters(nationality="American")
    assert us_count == 2

    # Test count by Brazilian nationality
    br_count = await repo.count_fighters(nationality="Brazilian")
    assert br_count == 1

    # Test count by Irish nationality
    ie_count = await repo.count_fighters(nationality="Irish")
    assert ie_count == 1

    # Test count by non-existent nationality
    jp_count = await repo.count_fighters(nationality="Japanese")
    assert jp_count == 0

    # Test total count without filter
    total_count = await repo.count_fighters()
    assert total_count == 5


@pytest.mark.asyncio
async def test_list_fighters_nationality_with_pagination(
    session: AsyncSession,
) -> None:
    """Verify that nationality filter works correctly with pagination."""

    # Create 5 American fighters
    for i in range(5):
        fighter = Fighter(
            id=f"us-fighter-{i}",
            name=f"American Fighter {i}",
            nationality="American",
            last_fight_date=date(2024, 1, i + 1),
        )
        session.add(fighter)

    # Create 2 Brazilian fighters
    for i in range(2):
        fighter = Fighter(
            id=f"br-fighter-{i}",
            name=f"Brazilian Fighter {i}",
            nationality="Brazilian",
            last_fight_date=date(2024, 2, i + 1),
        )
        session.add(fighter)

    await session.flush()

    repo = PostgreSQLFighterRepository(session)

    # Test first page of American fighters (limit=2, offset=0)
    page_1 = list(await repo.list_fighters(nationality="American", limit=2, offset=0))
    assert len(page_1) == 2
    assert all(f.nationality == "American" for f in page_1)

    # Test second page of American fighters (limit=2, offset=2)
    page_2 = list(await repo.list_fighters(nationality="American", limit=2, offset=2))
    assert len(page_2) == 2
    assert all(f.nationality == "American" for f in page_2)

    # Test third page of American fighters (limit=2, offset=4)
    page_3 = list(await repo.list_fighters(nationality="American", limit=2, offset=4))
    assert len(page_3) == 1
    assert all(f.nationality == "American" for f in page_3)

    # Test Brazilian fighters with pagination
    br_page = list(
        await repo.list_fighters(nationality="Brazilian", limit=10, offset=0)
    )
    assert len(br_page) == 2
    assert all(f.nationality == "Brazilian" for f in br_page)
