from __future__ import annotations

import json
import json
from datetime import UTC, date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("pytest_asyncio")

pytest_asyncio = pytest.importorskip("pytest_asyncio")
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.db.models import Base, Fight, Fighter, FighterStats, fighter_stats
from backend.db.repositories import PostgreSQLFighterRepository
from backend.schemas.fighter import FighterDetail
from scripts.load_scraped_data import (
    calculate_fighter_stats,
    calculate_longest_win_streak,
    load_fighter_detail,
)


@pytest_asyncio.fixture
async def session() -> AsyncSession:
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


@pytest.fixture
def fight_history_with_rich_metrics() -> list[dict[str, Any]]:
    """Provide diversified fight samples for accuracy, submissions, and duration checks."""

    return [
        {
            "event_date": "2024-05-01",
            "result": "W",
            "round": 3,
            "time": "04:30",
            "stats": {
                "sig_strikes": "45",
                "total_strikes": "80",
                "takedowns": "3",
                "knockdowns": "0",
                "submissions": "2",
            },
        },
        {
            "event_date": "2024-03-01",
            "result": "W",
            "round": 2,
            "time": "03:00",
            "stats": {
                "sig_strikes": "35",
                "total_strikes": "70",
                "takedowns": "2",
                "knockdowns": "1",
                "submissions": "1",
            },
        },
    ]


@pytest.fixture
def summary_stats_payload() -> dict[str, dict[str, Any]]:
    return {
        "career_statistics": {
            "slpm": "5.35",
            "str_acc": "52%",
            "sapm": "3.10",
            "str_def": "55%",
            "td_avg": "2.00",
            "td_acc": "44%",
            "td_def": "78%",
            "sub_avg": "1.2",
        }
    }


def test_calculate_fighter_stats_averages(
    fight_history_with_rich_metrics: list[dict[str, Any]],
    summary_stats_payload: dict[str, dict[str, Any]],
) -> None:
    """Aggregate averages should normalise fight data and merge scraper summaries."""

    aggregated = calculate_fighter_stats(
        fight_history_with_rich_metrics, summary_stats=summary_stats_payload
    )

    significant = aggregated["significant_strikes"]
    assert significant["sig_strikes_landed_per_min"] == "5.35"
    assert significant["sig_strikes_absorbed_per_min"] == "3.10"
    assert significant["sig_strikes_accuracy_pct"] == "52%"
    assert significant["sig_strikes_defense_pct"] == "55%"
    assert significant["sig_strikes_landed_avg"] == "40"

    striking = aggregated["striking"]
    assert striking["total_strikes_landed_avg"] == "75"
    assert striking["avg_knockdowns"] == "0.5"
    assert striking["sig_strikes_accuracy_pct"] == "52%"

    takedowns = aggregated["takedown_stats"]
    assert takedowns["takedowns_completed_avg"] == "2.5"
    assert takedowns["takedown_accuracy_pct"] == "44%"
    assert takedowns["takedown_defense_pct"] == "78%"

    grappling = aggregated["grappling"]
    assert grappling["takedowns_avg"] == "2.5"
    assert grappling["takedown_accuracy_pct"] == "44%"
    assert grappling["takedown_defense_pct"] == "78%"
    assert grappling["avg_submissions"] == "1.5"
    assert grappling["total_submissions"] == "3"

    career = aggregated["career"]
    assert career["avg_fight_duration_seconds"] == "675"
    assert career["longest_win_streak"] == "2"


@pytest.mark.asyncio
async def test_stats_summary_includes_derived_metrics(session: AsyncSession) -> None:
    fighter_one = Fighter(id="fighter-one", name="Fighter One")
    fighter_two = Fighter(id="fighter-two", name="Fighter Two")
    session.add_all([fighter_one, fighter_two])
    await session.flush()

    await session.execute(
        insert(fighter_stats),
        [
            {
                "fighter_id": "fighter-one",
                "category": "significant_strikes",
                "metric": "sig_strikes_accuracy_pct",
                "value": "50%",
            },
            {
                "fighter_id": "fighter-two",
                "category": "significant_strikes",
                "metric": "sig_strikes_accuracy_pct",
                "value": "60%",
            },
            {
                "fighter_id": "fighter-one",
                "category": "takedown_stats",
                "metric": "takedown_accuracy_pct",
                "value": "40%",
            },
            {
                "fighter_id": "fighter-two",
                "category": "takedown_stats",
                "metric": "takedown_accuracy_pct",
                "value": "50%",
            },
            {
                "fighter_id": "fighter-one",
                "category": "grappling",
                "metric": "avg_submissions",
                "value": "1.0",
            },
            {
                "fighter_id": "fighter-two",
                "category": "grappling",
                "metric": "avg_submissions",
                "value": "2.0",
            },
            {
                "fighter_id": "fighter-one",
                "category": "career",
                "metric": "avg_fight_duration_seconds",
                "value": "600",
            },
            {
                "fighter_id": "fighter-two",
                "category": "career",
                "metric": "avg_fight_duration_seconds",
                "value": "300",
            },
        ],
    )
    await session.commit()

    repo = PostgreSQLFighterRepository(session)
    summary = await repo.stats_summary()

    metrics = {metric.id: metric.value for metric in summary.metrics}
    assert metrics["fighters_indexed"] == 2
    assert metrics["avg_sig_strikes_accuracy_pct"] == pytest.approx(55.0, rel=1e-3)
    assert metrics["avg_takedown_accuracy_pct"] == pytest.approx(45.0, rel=1e-3)
    assert metrics["avg_submission_attempts"] == pytest.approx(1.5, rel=1e-3)
    assert metrics["avg_fight_duration_minutes"] == pytest.approx(7.5, rel=1e-3)


def test_calculate_fighter_stats_handles_missing_values() -> None:
    fights = [
        {
            "stats": {
                "sig_strikes": "--",
                "sig_strikes_pct": None,
                "total_strikes": None,
                "takedowns": None,
            }
        },
        {"stats": {}},
    ]

    aggregated = calculate_fighter_stats(fights)

    assert aggregated == {}


def test_calculate_longest_win_streak_orders_by_event_date() -> None:
    """Win streak helper should evaluate chronological order regardless of input ordering."""

    fights: list[dict[str, Any]] = [
        {"event_date": "2024-05-01", "result": "W"},
        {"event_date": "2024-01-01", "result": "W"},
        {"event_date": "2024-02-01", "result": "W"},
        {"event_date": "2024-03-01", "result": "W"},
        {"event_date": "2024-04-01", "result": "L"},
    ]

    assert calculate_longest_win_streak(fights) == 3


@pytest.mark.asyncio
async def test_get_fighter_returns_aggregated_stats(session: AsyncSession) -> None:
    fighter = Fighter(
        id="test-fighter",
        name="Test Fighter",
        nickname=None,
        division=None,
        height=None,
        weight=None,
        reach=None,
        leg_reach=None,
        stance=None,
        dob=None,
        record=None,
    )
    session.add(fighter)
    await session.flush()

    await session.execute(
        insert(fighter_stats),
        [
            {
                "fighter_id": fighter.id,
                "category": "significant_strikes",
                "metric": "sig_strikes_accuracy_pct",
                "value": "52%",
            },
            {
                "fighter_id": fighter.id,
                "category": "striking",
                "metric": "total_strikes_landed_avg",
                "value": "75",
            },
            {
                "fighter_id": fighter.id,
                "category": "grappling",
                "metric": "avg_submissions",
                "value": "1.5",
            },
        ],
    )
    await session.commit()

    repo = PostgreSQLFighterRepository(session)
    detail = await repo.get_fighter(fighter.id)

    assert detail is not None
    assert detail.significant_strikes["sig_strikes_accuracy_pct"] == "52%"
    assert detail.striking["total_strikes_landed_avg"] == "75"
    assert detail.grappling["avg_submissions"] == "1.5"


@pytest.mark.asyncio
async def test_get_fighter_orders_mixed_fight_history(session: AsyncSession) -> None:
    """Ensure upcoming bouts precede past fights sorted by recency."""

    # Create a fighter record to anchor the upcoming and historical fights.
    fighter: Fighter = Fighter(id="fighter-ordering", name="Ordering Test")
    session.add_all([fighter, FighterStats(fighter_id=fighter.id)])
    await session.flush()

    # Define precise event dates to make the intended ordering explicit.
    upcoming_date: date = date(2025, 1, 1)
    recent_past_date: date = date(2024, 5, 15)
    oldest_past_date: date = date(2023, 9, 10)

    # Construct fights with type annotations so ordering expectations are unambiguous for readers.
    upcoming_fight: Fight = Fight(
        id="fight-upcoming",
        fighter_id=fighter.id,
        opponent_id="opponent-upcoming",
        opponent_name="Future Opponent",
        event_name="Future Event",
        event_date=upcoming_date,
        result="next",
        method=None,
        round=None,
        time=None,
        fight_card_url="https://example.com/future",
    )
    recent_past_fight: Fight = Fight(
        id="fight-recent",
        fighter_id=fighter.id,
        opponent_id="opponent-recent",
        opponent_name="Recent Opponent",
        event_name="Recent Event",
        event_date=recent_past_date,
        result="W",
        method="Decision",
        round=3,
        time="05:00",
        fight_card_url="https://example.com/recent",
    )
    oldest_past_fight: Fight = Fight(
        id="fight-oldest",
        fighter_id=fighter.id,
        opponent_id="opponent-oldest",
        opponent_name="Oldest Opponent",
        event_name="Oldest Event",
        event_date=oldest_past_date,
        result="L",
        method="Submission",
        round=1,
        time="01:30",
        fight_card_url="https://example.com/oldest",
    )

    session.add_all([upcoming_fight, recent_past_fight, oldest_past_fight])
    await session.commit()

    repository = PostgreSQLFighterRepository(session)
    fighter_detail: FighterDetail | None = await repository.get_fighter(fighter.id)

    assert fighter_detail is not None

    ordered_results: list[tuple[str, date | None]] = [
        (entry.result, entry.event_date) for entry in fighter_detail.fight_history
    ]

    expected_order: list[tuple[str, date | None]] = [
        ("next", upcoming_date),
        ("W", recent_past_date),
        ("L", oldest_past_date),
    ]

    # The repository should report upcoming fights first and sort past results in reverse chronological order.
    assert ordered_results == expected_order


@pytest.mark.asyncio
async def test_get_fighter_populates_age_from_dob(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Repository should calculate age in years using a timezone-aware 'today'."""

    class FixedDateTime(datetime):
        """Custom datetime shim that consistently returns the reference date in UTC."""

        @classmethod
        def now(cls, tz: timezone | None = None) -> datetime:  # type: ignore[override]
            reference_moment: datetime = datetime(2024, 6, 16, tzinfo=UTC)
            return reference_moment if tz is None else reference_moment.astimezone(tz)

    monkeypatch.setattr("backend.db.repositories.datetime", FixedDateTime)

    fighter: Fighter = Fighter(
        id="fighter-with-dob",
        name="Age Checked",
        dob=date(1990, 6, 15),
    )
    session.add(fighter)
    await session.commit()

    repository = PostgreSQLFighterRepository(session)
    detail: FighterDetail | None = await repository.get_fighter(fighter.id)

    assert detail is not None
    assert detail.age == 34


@pytest.mark.asyncio
async def test_get_fighter_returns_none_age_when_dob_missing(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing DOB entries should propagate a ``None`` age without raising errors."""

    class FixedDateTime(datetime):
        """Mirror the deterministic UTC reference used in the sibling age test."""

        @classmethod
        def now(cls, tz: timezone | None = None) -> datetime:  # type: ignore[override]
            reference_moment: datetime = datetime(2024, 6, 16, tzinfo=UTC)
            return reference_moment if tz is None else reference_moment.astimezone(tz)

    monkeypatch.setattr("backend.db.repositories.datetime", FixedDateTime)

    fighter: Fighter = Fighter(
        id="fighter-without-dob",
        name="No DOB",
        dob=None,
    )
    session.add(fighter)
    await session.commit()

    repository = PostgreSQLFighterRepository(session)
    detail: FighterDetail | None = await repository.get_fighter(fighter.id)

    assert detail is not None
    assert detail.age is None


@pytest.mark.asyncio
async def test_get_fighter_merges_cached_fight_breakdowns(
    session: AsyncSession,
) -> None:
    """fighter_stats rows should backfill fight history metrics for the API."""

    fighter = Fighter(id="fighter-breakdown", name="Breakdown Subject")
    fight = Fight(
        id="fight-breakdown",
        fighter_id=fighter.id,
        opponent_id="opponent-merge",
        opponent_name="Merge Opponent",
        event_name="Merge Event",
        event_date=date(2024, 1, 1),
        result="W",
        method=None,
        round=None,
        time=None,
        fight_card_url=None,
        stats={},
    )

    session.add_all([fighter, fight])
    await session.flush()

    cached_payload = {
        "fight_id": fight.id,
        "event_name": "Merge Event",
        "event_date": "2024-01-01",
        "opponent": "Merge Opponent",
        "opponent_id": "opponent-merge",
        "result": "W",
        "method": "KO/TKO",
        "round": 2,
        "time": "01:15",
        "fight_card_url": "https://example.com/merge",
        "stats": {"sig_strikes": "88", "takedowns": "3"},
    }

    await session.execute(
        insert(fighter_stats),
        [
            {
                "fighter_id": fighter.id,
                "category": "fight_history",
                "metric": fight.id,
                "value": json.dumps(cached_payload, sort_keys=True),
            }
        ],
    )
    await session.commit()

    repository = PostgreSQLFighterRepository(session)
    detail = await repository.get_fighter(fighter.id)

    assert detail is not None
    assert detail.fight_history, "Expected fight history populated from cached payload."
    entry = detail.fight_history[0]
    assert entry.stats["sig_strikes"] == "88"
    assert entry.stats["takedowns"] == "3"
    assert entry.method == "KO/TKO"
    assert entry.round == 2
    assert entry.time == "01:15"
    assert entry.fight_card_url == "https://example.com/merge"


@pytest.mark.asyncio
async def test_load_fighter_detail_persists_fight_stats(
    session: AsyncSession, tmp_path: Path
) -> None:
    """Verify fight stats dictionaries are saved when present in the source payload."""

    fight_stats_payload: dict[str, str] = {
        "knockdowns": "1",
        "total_strikes": "85",
        "takedowns": "2",
        "submissions": "0",
    }
    fighter_payload: dict[str, Any] = {
        "fighter_id": "loader-fighter",
        "name": "Loader Fighter",
        "fight_history": [
            {
                "fight_id": "loader-fight-1",
                "event_name": "Loader Event",
                "event_date": "2024-01-01",
                "opponent": "Test Opponent",
                "result": "W",
                "method": "Decision",
                "round": 3,
                "time": "05:00",
                "fight_card_url": "https://example.com/fight",
                "stats": fight_stats_payload,
            }
        ],
    }
    detail_path: Path = tmp_path / "loader_fighter.json"
    detail_path.write_text(json.dumps(fighter_payload), encoding="utf-8")

    assert await load_fighter_detail(session, detail_path) is True

    stored_fight: Fight | None = await session.get(Fight, "loader-fight-1")
    assert stored_fight is not None
    assert stored_fight.stats == fight_stats_payload

    rows = await session.execute(
        select(fighter_stats.c.metric, fighter_stats.c.value).where(
            fighter_stats.c.fighter_id == "loader-fighter",
            fighter_stats.c.category == "fight_history",
        )
    )
    fight_rows = rows.all()
    assert len(fight_rows) == 1
    metric, raw_value = fight_rows[0]
    assert metric == "loader-fight-1"
    decoded = json.loads(raw_value)
    assert decoded["fight_id"] == "loader-fight-1"
    assert decoded["stats"]["knockdowns"] == "1"


@pytest.mark.asyncio
async def test_load_fighter_detail_defaults_missing_stats(
    session: AsyncSession, tmp_path: Path
) -> None:
    """Ensure fights without stats payloads are stored with empty dictionaries."""

    fighter_payload: dict[str, Any] = {
        "fighter_id": "loader-fighter-no-stats",
        "name": "Loader Fighter No Stats",
        "fight_history": [
            {
                "fight_id": "loader-fight-2",
                "event_name": "Loader Event",
                "event_date": "2024-02-02",
                "opponent": "Opponent",
                "result": "L",
                "method": "KO",
                "round": 1,
                "time": "01:30",
                "fight_card_url": None,
                # No explicit stats dictionary ensures we exercise the defaulting branch.
            }
        ],
    }
    detail_path: Path = tmp_path / "loader_fighter_missing_stats.json"
    detail_path.write_text(json.dumps(fighter_payload), encoding="utf-8")

    assert await load_fighter_detail(session, detail_path) is True

    stored_fight: Fight | None = await session.get(Fight, "loader-fight-2")
    assert stored_fight is not None
    assert stored_fight.stats == {}


@pytest.mark.asyncio
async def test_compare_fighters_returns_stats(session: AsyncSession) -> None:
    first = Fighter(id="alpha", name="Alpha", record="10-2-0", division="Lightweight")
    second = Fighter(id="bravo", name="Bravo", record="8-1-0", division="Lightweight")
    session.add_all([first, second])
    await session.flush()

    await session.execute(
        insert(fighter_stats),
        [
            {
                "fighter_id": "alpha",
                "category": "significant_strikes",
                "metric": "sig_strikes_accuracy_pct",
                "value": "55%",
            },
            {
                "fighter_id": "bravo",
                "category": "significant_strikes",
                "metric": "sig_strikes_accuracy_pct",
                "value": "60%",
            },
            {
                "fighter_id": "alpha",
                "category": "grappling",
                "metric": "avg_submissions",
                "value": "1.0",
            },
            {
                "fighter_id": "bravo",
                "category": "grappling",
                "metric": "avg_submissions",
                "value": "1.5",
            },
        ],
    )
    await session.commit()

    repo = PostgreSQLFighterRepository(session)
    comparison = await repo.get_fighters_for_comparison(["alpha", "bravo"])

    assert [entry.fighter_id for entry in comparison] == ["alpha", "bravo"]
    assert comparison[0].significant_strikes["sig_strikes_accuracy_pct"] == "55%"
    assert comparison[1].grappling["avg_submissions"] == "1.5"


@pytest.mark.asyncio
async def test_search_fighters_supports_pagination(session: AsyncSession) -> None:
    fighters = [
        Fighter(id="alpha", name="Alpha Fighter"),
        Fighter(id="albert", name="Albert Champion"),
        Fighter(id="bravo", name="Bravo Contender"),
    ]
    session.add_all(fighters)
    await session.flush()

    repo = PostgreSQLFighterRepository(session)
    page_one, total = await repo.search_fighters(query="Al", limit=1, offset=0)
    page_two, _ = await repo.search_fighters(query="Al", limit=1, offset=1)

    assert total == 2
    assert len(page_one) == 1
    assert len(page_two) == 1
    assert page_one[0].name.startswith("Alpha")
    assert page_two[0].name.startswith("Albert")


@pytest.mark.asyncio
async def test_search_fighters_filters_by_extended_win_streak(
    session: AsyncSession,
) -> None:
    """Ensure win streak filtering looks beyond the default six-fight window."""

    streaking_fighter = Fighter(id="streaker", name="Seven Streak")
    challenger = Fighter(id="challenger", name="Challenger Five")
    session.add_all([streaking_fighter, challenger])
    await session.flush()

    # Upcoming fight should be ignored when counting wins.
    session.add(
        Fight(
            id="streaker-upcoming",
            fighter_id="streaker",
            opponent_id="opponent-upcoming",
            opponent_name="Future Opponent",
            event_name="Future Event",
            event_date=date(2025, 1, 1),
            result="Next",
            method=None,
            round=None,
            time=None,
            fight_card_url=None,
        )
    )

    for index in range(7):
        session.add(
            Fight(
                id=f"streaker-win-{index}",
                fighter_id="streaker",
                opponent_id=f"opponent-{index}",
                opponent_name=f"Opponent {index}",
                event_name=f"Event {index}",
                event_date=date(2024, 1, 1 + index),
                result="Win",
                method="Decision",
                round=3,
                time="05:00",
                fight_card_url=None,
            )
        )

    for index in range(5):
        session.add(
            Fight(
                id=f"challenger-win-{index}",
                fighter_id="challenger",
                opponent_id=f"other-{index}",
                opponent_name=f"Other {index}",
                event_name=f"Challenger Event {index}",
                event_date=date(2024, 2, 1 + index),
                result="Win",
                method="Decision",
                round=3,
                time="05:00",
                fight_card_url=None,
            )
        )

    session.add(
        Fight(
            id="challenger-loss",
            fighter_id="challenger",
            opponent_id="other-loss",
            opponent_name="Loss Opponent",
            event_name="Loss Event",
            event_date=date(2024, 7, 1),
            result="Loss",
            method="Decision",
            round=3,
            time="05:00",
            fight_card_url=None,
        )
    )

    await session.commit()

    repo = PostgreSQLFighterRepository(session)
    fighters, total = await repo.search_fighters(
        streak_type="win",
        min_streak_count=6,
        include_streak=True,
    )

    assert total == 1
    assert [fighter.fighter_id for fighter in fighters] == ["streaker"]
    assert fighters[0].current_streak_type == "win"
    assert fighters[0].current_streak_count == 7
