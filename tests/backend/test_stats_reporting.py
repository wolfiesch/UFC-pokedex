from __future__ import annotations

from datetime import date

import pytest

try:
    import pytest_asyncio
    from sqlalchemy import insert
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    pytest.skip(
        f"Optional dependency '{exc.name}' is required for stats reporting tests.",
        allow_module_level=True,
    )

from backend.db.models import Base, Fight, Fighter, fighter_stats
from backend.db.repositories import PostgreSQLFighterRepository


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    """Create an in-memory SQLite session for repository testing."""

    pytest.importorskip("aiosqlite")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
        if session.in_transaction():
            await session.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_leaderboards_rank_by_numeric_value(session: AsyncSession) -> None:
    """Leaderboards should order fighters numerically after casting stat values."""

    fighters = [
        Fighter(
            id="fighter-1",
            name="Alice Accurate",
            nickname=None,
            division="Lightweight",
            height=None,
            weight=None,
            reach=None,
            leg_reach=None,
            stance=None,
            dob=None,
            record=None,
        ),
        Fighter(
            id="fighter-2",
            name="Bobby Balanced",
            nickname=None,
            division="Featherweight",
            height=None,
            weight=None,
            reach=None,
            leg_reach=None,
            stance=None,
            dob=None,
            record=None,
        ),
        Fighter(
            id="fighter-3",
            name="Charlie Classic",
            nickname=None,
            division="Welterweight",
            height=None,
            weight=None,
            reach=None,
            leg_reach=None,
            stance=None,
            dob=None,
            record=None,
        ),
    ]
    session.add_all(fighters)

    fights = [
        Fight(
            id="fight-1",
            fighter_id="fighter-1",
            opponent_id=None,
            opponent_name="Opponent 1",
            event_name="Event 1",
            event_date=date(2024, 1, 1),
            result="Win",
            method="Decision",
            round=1,
            time="3:30",
            fight_card_url=None,
        ),
        Fight(
            id="fight-2",
            fighter_id="fighter-2",
            opponent_id=None,
            opponent_name="Opponent 2",
            event_name="Event 2",
            event_date=date(2024, 2, 1),
            result="Win",
            method="Decision",
            round=1,
            time="3:00",
            fight_card_url=None,
        ),
        Fight(
            id="fight-3",
            fighter_id="fighter-3",
            opponent_id=None,
            opponent_name="Opponent 3",
            event_name="Event 3",
            event_date=date(2023, 5, 1),
            result="Win",
            method="Decision",
            round=1,
            time="3:00",
            fight_card_url=None,
        ),
    ]
    session.add_all(fights)

    await session.execute(
        insert(fighter_stats),
        [
            {
                "fighter_id": "fighter-1",
                "category": "striking",
                "metric": "sig_strikes_accuracy_pct",
                "value": "45%",
            },
            {
                "fighter_id": "fighter-1",
                "category": "grappling",
                "metric": "avg_submissions",
                "value": "2.0",
            },
            {
                "fighter_id": "fighter-2",
                "category": "striking",
                "metric": "sig_strikes_accuracy_pct",
                "value": "60%",
            },
            {
                "fighter_id": "fighter-2",
                "category": "grappling",
                "metric": "avg_submissions",
                "value": "3.0",
            },
            {
                "fighter_id": "fighter-3",
                "category": "striking",
                "metric": "sig_strikes_accuracy_pct",
                "value": "90%",
            },
            {
                "fighter_id": "fighter-3",
                "category": "grappling",
                "metric": "avg_submissions",
                "value": "5.0",
            },
        ],
    )
    await session.commit()

    repository = PostgreSQLFighterRepository(session)
    response = await repository.get_leaderboards(
        limit=5,
        accuracy_metric="sig_strikes_accuracy_pct",
        submissions_metric="avg_submissions",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )

    accuracy_ids = [entry.fighter_id for entry in response.accuracy.entries]
    submission_ids = [entry.fighter_id for entry in response.submissions.entries]

    assert accuracy_ids == ["fighter-2", "fighter-1"]
    assert submission_ids == ["fighter-2", "fighter-1"]


@pytest.mark.asyncio
async def test_trends_calculate_streaks_and_durations(
    session: AsyncSession,
) -> None:
    """Trends should include longest streaks and average duration aggregates."""

    fighters = [
        Fighter(
            id="streaker-1",
            name="Donna Durable",
            nickname=None,
            division="Lightweight",
            height=None,
            weight=None,
            reach=None,
            leg_reach=None,
            stance=None,
            dob=None,
            record=None,
        ),
        Fighter(
            id="streaker-2",
            name="Evan Efficient",
            nickname=None,
            division="Featherweight",
            height=None,
            weight=None,
            reach=None,
            leg_reach=None,
            stance=None,
            dob=None,
            record=None,
        ),
    ]
    session.add_all(fighters)

    streak_fights = [
        Fight(
            id="s1",
            fighter_id="streaker-1",
            opponent_id=None,
            opponent_name="Opponent A",
            event_name="Event A",
            event_date=date(2024, 1, 1),
            result="Win",
            method="Decision",
            round=1,
            time="3:30",
            fight_card_url=None,
        ),
        Fight(
            id="s2",
            fighter_id="streaker-1",
            opponent_id=None,
            opponent_name="Opponent B",
            event_name="Event B",
            event_date=date(2024, 2, 1),
            result="Win",
            method="Decision",
            round=2,
            time="1:10",
            fight_card_url=None,
        ),
        Fight(
            id="s3",
            fighter_id="streaker-1",
            opponent_id=None,
            opponent_name="Opponent C",
            event_name="Event C",
            event_date=date(2024, 3, 1),
            result="Loss",
            method="Decision",
            round=3,
            time="2:00",
            fight_card_url=None,
        ),
        Fight(
            id="s4",
            fighter_id="streaker-2",
            opponent_id=None,
            opponent_name="Opponent D",
            event_name="Event D",
            event_date=date(2024, 1, 15),
            result="Win",
            method="Decision",
            round=1,
            time="0:30",
            fight_card_url=None,
        ),
        Fight(
            id="s5",
            fighter_id="streaker-2",
            opponent_id=None,
            opponent_name="Opponent E",
            event_name="Event E",
            event_date=date(2024, 1, 28),
            result="Win",
            method="Decision",
            round=2,
            time="2:30",
            fight_card_url=None,
        ),
        Fight(
            id="s6",
            fighter_id="streaker-2",
            opponent_id=None,
            opponent_name="Opponent F",
            event_name="Event F",
            event_date=date(2024, 2, 10),
            result="Win",
            method="Decision",
            round=3,
            time="5:00",
            fight_card_url=None,
        ),
        Fight(
            id="s7",
            fighter_id="streaker-2",
            opponent_id=None,
            opponent_name="Opponent G",
            event_name="Event G",
            event_date=date(2024, 3, 5),
            result="Win",
            method="Decision",
            round=1,
            time="4:00",
            fight_card_url=None,
        ),
    ]
    session.add_all(streak_fights)
    await session.commit()

    repository = PostgreSQLFighterRepository(session)
    response = await repository.get_trends(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        time_bucket="month",
        streak_limit=2,
    )

    assert [entry.fighter_id for entry in response.longest_win_streaks] == [
        "streaker-2",
        "streaker-1",
    ]
    assert response.longest_win_streaks[0].streak == 4

    january_buckets = [
        bucket
        for bucket in response.average_fight_durations
        if bucket.bucket_label == "Jan 2024"
    ]
    assert january_buckets, "January bucket should be present"

    featherweight_bucket = next(
        bucket for bucket in january_buckets if bucket.division == "Featherweight"
    )
    # Average duration should be (30 seconds + 450 seconds) / 2 == 240 seconds.
    assert abs(featherweight_bucket.average_duration_seconds - 240.0) < 1e-6
