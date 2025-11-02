from __future__ import annotations

import pytest

pytest.importorskip("sqlalchemy")

pytest_asyncio = pytest.importorskip("pytest_asyncio")
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.db.models import Base, Fighter, fighter_stats
from backend.db.repositories import PostgreSQLFighterRepository
from scripts.load_scraped_data import calculate_fighter_stats


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


def test_calculate_fighter_stats_averages() -> None:
    fights = [
        {
            "stats": {
                "sig_strikes": "20 of 40",
                "sig_strikes_pct": "50%",
                "total_strikes": "60 of 120",
                "takedowns": "2 of 4",
            }
        },
        {
            "stats": {
                "sig_strikes": "30 of 60",
                "sig_strikes_pct": "50%",
                "total_strikes": "50 of 100",
                "takedowns": "3 of 6",
            }
        },
    ]

    aggregated = calculate_fighter_stats(fights)

    assert aggregated["significant_strikes"]["avg_landed"] == "25"
    assert aggregated["significant_strikes"]["avg_attempted"] == "50"
    assert aggregated["significant_strikes"]["accuracy_pct"] == "50%"
    assert aggregated["striking"]["total_strikes_landed_avg"] == "55"
    assert aggregated["striking"]["total_strikes_attempted_avg"] == "110"
    assert aggregated["striking"]["total_strikes_accuracy_pct"] == "50%"
    assert aggregated["takedown_stats"]["takedowns_completed_avg"] == "2.5"
    assert aggregated["takedown_stats"]["takedowns_attempted_avg"] == "5"
    assert aggregated["takedown_stats"]["takedown_accuracy_pct"] == "50%"
    assert aggregated["grappling"]["takedowns_avg"] == "2.5"
    assert aggregated["grappling"]["takedown_accuracy_pct"] == "50%"


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
