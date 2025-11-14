from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, datetime

import pytest

try:
    import pytest_asyncio
    from sqlalchemy.ext.asyncio import AsyncSession
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    pytest.skip(
        f"Optional dependency '{exc.name}' is required for odds repository tests.",
        allow_module_level=True,
    )

from backend.db.models import Base, Fighter, FighterOdds
from backend.db.repositories.odds import OddsRepository
from tests.backend.postgres import TemporaryPostgresSchema, postgres_schema  # noqa: F401


def _make_history() -> list[dict[str, float | int | str]]:
    return [
        {"timestamp_ms": 1700000000000, "timestamp": "2023-11-14T00:00:00Z", "odds": 2.1},
        {"timestamp_ms": 1700003600000, "timestamp": "2023-11-14T01:00:00Z", "odds": 2.05},
    ]


@pytest_asyncio.fixture()
async def session(
    postgres_schema: TemporaryPostgresSchema,
) -> AsyncIterator[AsyncSession]:
    async with postgres_schema.session_scope(Base.metadata) as session:
        yield session


@pytest.mark.asyncio
async def test_list_fighter_odds_orders_by_event_and_scrape(session: AsyncSession) -> None:
    fighter = Fighter(id="fighter-a", name="Alpha")
    session.add(fighter)
    odds_newer = FighterOdds(
        id="odds-newer",
        fighter_id=fighter.id,
        opponent_name="Opponent B",
        event_name="Event B",
        event_date=date(2024, 2, 1),
        event_url="https://events.example/b",
        opening_odds="+150",
        closing_range_start="+120",
        closing_range_end="+130",
        mean_odds_history=_make_history(),
        num_odds_points=2,
        data_quality_tier="excellent",
        scraped_at=datetime(2024, 1, 15, 12, 0, 0),
    )
    odds_older = FighterOdds(
        id="odds-older",
        fighter_id=fighter.id,
        opponent_name="Opponent A",
        event_name="Event A",
        event_date=date(2023, 12, 1),
        event_url="https://events.example/a",
        opening_odds="+200",
        closing_range_start="+210",
        closing_range_end="+220",
        mean_odds_history=_make_history(),
        num_odds_points=2,
        data_quality_tier="good",
        scraped_at=datetime(2023, 11, 1, 0, 0, 0),
    )
    odds_null_date = FighterOdds(
        id="odds-no-date",
        fighter_id=fighter.id,
        opponent_name="Opponent C",
        event_name="Event C",
        event_date=None,
        event_url=None,
        opening_odds="-120",
        closing_range_start="-110",
        closing_range_end="-115",
        mean_odds_history=_make_history(),
        num_odds_points=2,
        data_quality_tier="usable",
        scraped_at=datetime(2024, 3, 1, 12, 0, 0),
    )
    session.add_all([odds_newer, odds_older, odds_null_date])
    await session.commit()

    repo = OddsRepository(session)
    rows = await repo.list_fighter_odds(fighter.id, limit=10)

    assert [row.id for row in rows] == ["odds-newer", "odds-older", "odds-no-date"]


@pytest.mark.asyncio
async def test_quality_filters_affect_counts(session: AsyncSession) -> None:
    fighter = Fighter(id="fighter-b", name="Bravo")
    session.add(fighter)
    session.add_all(
        [
            FighterOdds(
                id="odds-excellent",
                fighter_id=fighter.id,
                opponent_name="Opp 1",
                event_name="Event 1",
                event_date=None,
                mean_odds_history=_make_history(),
                num_odds_points=60,
                data_quality_tier="excellent",
                scraped_at=datetime(2024, 1, 1),
            ),
            FighterOdds(
                id="odds-poor",
                fighter_id=fighter.id,
                opponent_name="Opp 2",
                event_name="Event 2",
                event_date=None,
                mean_odds_history=_make_history(),
                num_odds_points=4,
                data_quality_tier="poor",
                scraped_at=datetime(2024, 1, 2),
            ),
        ]
    )
    await session.commit()

    repo = OddsRepository(session)
    total = await repo.count_fighter_odds(fighter.id)
    filtered = await repo.count_fighter_odds(fighter.id, min_quality="good")

    assert total == 2
    assert filtered == 1

    rows = await repo.list_fighter_odds(fighter.id, min_quality="good")
    assert [row.id for row in rows] == ["odds-excellent"]


@pytest.mark.asyncio
async def test_quality_stats_reflects_dataset(session: AsyncSession) -> None:
    fighter1 = Fighter(id="fighter-c", name="Charlie")
    fighter2 = Fighter(id="fighter-d", name="Delta")
    session.add_all([fighter1, fighter2])
    session.add(
        FighterOdds(
            id="odds-c",
            fighter_id=fighter1.id,
            opponent_name="Opp C",
            event_name="Event C",
            event_date=None,
            mean_odds_history=_make_history(),
            num_odds_points=55,
            data_quality_tier="excellent",
            scraped_at=datetime(2024, 1, 3),
        )
    )
    await session.commit()

    repo = OddsRepository(session)
    stats = await repo.get_quality_stats()

    assert stats["total_records"] == 1
    assert stats["unique_fighters"] == 1
    assert stats["coverage"]["total_fighters"] == 2
    assert stats["coverage"]["fighters_with_odds"] == 1
    assert stats["quality_distribution"]["excellent"] == 1
    assert stats["quality_distribution"]["good"] == 0
