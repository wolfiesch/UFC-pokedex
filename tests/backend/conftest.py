"""Shared backend test fixtures for asynchronous database access and stats scenarios."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.db.models import Base


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Provide an in-memory SQLite session for integration-style tests."""
    pytest.importorskip("aiosqlite")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db_session:
        yield db_session
        if db_session.in_transaction():
            await db_session.rollback()
    await engine.dispose()


@pytest.fixture
def leaderboard_payload() -> list[dict[str, Any]]:
    """Synthetic leaderboard rows used by API and serializer tests."""
    return [
        {
            "fighter_id": "alpha-1",
            "fighter_name": "Alpha One",
            "metric": "striking_accuracy",
            "value": 0.64,
            "sample_size": 5,
        },
        {
            "fighter_id": "bravo-2",
            "fighter_name": "Bravo Two",
            "metric": "striking_accuracy",
            "value": 0.58,
            "sample_size": 4,
        },
        {
            "fighter_id": "charlie-3",
            "fighter_name": "Charlie Three",
            "metric": "striking_accuracy",
            "value": 0.55,
            "sample_size": 6,
        },
    ]


@pytest.fixture
def trend_payload() -> list[dict[str, Any]]:
    """Synthetic rolling average data representing recent performance trends."""
    return [
        {
            "fighter_id": "alpha-1",
            "fighter_name": "Alpha One",
            "metric": "sig_strikes_landed_per_min",
            "points": [
                {"label": date(2024, 1, 1), "value": 3.1},
                {"label": date(2024, 2, 1), "value": 3.4},
                {"label": date(2024, 3, 1), "value": 3.7},
            ],
        },
        {
            "fighter_id": "bravo-2",
            "fighter_name": "Bravo Two",
            "metric": "takedown_success_rate",
            "points": [
                {"label": date(2024, 1, 1), "value": 0.45},
                {"label": date(2024, 2, 1), "value": 0.5},
                {"label": date(2024, 3, 1), "value": 0.52},
            ],
        },
    ]
