from __future__ import annotations

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Fighter, fighter_stats
from backend.db.repositories import PostgreSQLFighterRepository
from scripts.load_scraped_data import calculate_fighter_stats


def test_calculate_fighter_stats_averages() -> None:
    fights = [
        {
            "stats": {
                "sig_strikes": "20",
                "sig_strikes_pct": "50%",
                "total_strikes": "60",
                "takedowns": "2",
                "knockdowns": "3",
                "submissions": "1",
            }
        },
        {
            "stats": {
                "sig_strikes": "30",
                "sig_strikes_pct": "50%",
                "total_strikes": "50",
                "takedowns": "1",
                "knockdowns": "1",
                "submissions": "1",
            }
        },
    ]

    aggregated = calculate_fighter_stats(fights)

    assert aggregated["striking"]["avg_total_strikes"] == "55"
    assert aggregated["striking"]["avg_knockdowns"] == "2"
    assert aggregated["grappling"]["avg_takedowns"] == "1.5"
    assert aggregated["grappling"]["avg_submissions"] == "1"
    assert aggregated["takedown_stats"]["avg_takedowns"] == "1.5"


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
                "metric": "avg_landed",
                "value": "25",
            },
            {
                "fighter_id": fighter.id,
                "category": "striking",
                "metric": "total_strikes_accuracy_pct",
                "value": "45%",
            },
            {
                "fighter_id": fighter.id,
                "category": "grappling",
                "metric": "takedowns_avg",
                "value": "2.5",
            },
        ],
    )
    await session.commit()

    repo = PostgreSQLFighterRepository(session)
    detail = await repo.get_fighter(fighter.id)

    assert detail is not None
    assert detail.significant_strikes["avg_landed"] == "25"
    assert detail.striking["total_strikes_accuracy_pct"] == "45%"
    assert detail.grappling["takedowns_avg"] == "2.5"
