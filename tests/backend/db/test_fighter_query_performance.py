"""Tests for query performance optimization."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

try:
    import pytest_asyncio
    from sqlalchemy import event
    from sqlalchemy.ext.asyncio import AsyncSession
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    pytest.skip(
        f"Optional dependency '{exc.name}' is required for query performance tests.",
        allow_module_level=True,
    )

from backend.db.models import Base, Fighter, Fight
from backend.db.repositories import PostgreSQLFighterRepository
from datetime import date
from tests.backend.postgres import (
    TemporaryPostgresSchema,
    postgres_schema,
)  # noqa: F401


@pytest_asyncio.fixture
async def session(
    postgres_schema: TemporaryPostgresSchema,
) -> AsyncIterator[AsyncSession]:
    """Provide an async session bound to a temporary PostgreSQL schema."""

    async with postgres_schema.session_scope(Base.metadata) as session:
        yield session


class QueryCounter:
    """Track number of SQL queries executed."""

    def __init__(self):
        self.count = 0
        self.queries = []

    def callback(self, conn, cursor, statement, parameters, context, executemany):
        self.count += 1
        self.queries.append(statement)


@pytest.mark.asyncio
async def test_get_fighter_detail_single_query(session: AsyncSession):
    """Test that fighter detail loads in minimal queries (no N+1)."""
    # Create test fighter with multiple fights
    fighter = Fighter(
        id="test-fighter-id",
        name="Test Fighter",
        division="Lightweight",
    )
    session.add(fighter)

    # Add multiple fights to trigger potential N+1
    for i in range(5):
        fight = Fight(
            id=f"fight-{i}",
            fighter_id="test-fighter-id",
            opponent_name=f"Opponent {i}",
            event_name=f"UFC Event {i}",
            event_date=date(2024, 1, 1),
            result="win" if i % 2 == 0 else "loss",
            method="KO/TKO",
            round=1,
            time="2:30",
        )
        session.add(fight)

    await session.commit()

    counter = QueryCounter()

    # Listen for queries on the engine
    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", counter.callback)

    repo = PostgreSQLFighterRepository(session)

    # Get fighter with fights
    result = await repo.get_fighter("test-fighter-id")

    # Should use fixed number of queries regardless of fight count (no N+1)
    # Optimized implementation uses:
    # 1. Fighter details + eager loaded fights (selectinload)
    # 2. Fighter stats
    # 3. Opponent perspective fights
    # Total: 3-4 queries (plus PRAGMA in SQLite)
    #
    # Before optimization: would have been 1 + N queries (one per fight)
    assert result is not None, "Fighter should be found"

    # Filter out PRAGMA queries (SQLite metadata)
    business_queries = [q for q in counter.queries if not q.startswith("PRAGMA")]
    query_count = len(business_queries)

    # Should use at most 4 business queries (fighter, fights, stats, opponent_fights)
    # More importantly, count should NOT scale with number of fights (no N+1)
    assert (
        query_count <= 4
    ), f"Used {query_count} queries (N+1 detected). Queries: {business_queries}"

    # Verify result has all fights loaded
    assert len(result.fight_history) == 5, "All fights should be loaded"

    event.remove(engine, "before_cursor_execute", counter.callback)


@pytest.mark.asyncio
async def test_query_count_does_not_scale_with_fights(session: AsyncSession):
    """Test that query count stays constant regardless of number of fights (proves no N+1)."""
    # Create fighter with 10 fights
    fighter = Fighter(
        id="fighter-many-fights",
        name="Fighter with Many Fights",
        division="Lightweight",
    )
    session.add(fighter)

    # Add 10 fights
    for i in range(10):
        fight = Fight(
            id=f"fight-many-{i}",
            fighter_id="fighter-many-fights",
            opponent_name=f"Opponent {i}",
            event_name=f"UFC Event {i}",
            event_date=date(2024, 1, 1),
            result="win",
            method="KO/TKO",
            round=1,
            time="2:30",
        )
        session.add(fight)

    await session.commit()

    counter = QueryCounter()
    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", counter.callback)

    repo = PostgreSQLFighterRepository(session)
    result = await repo.get_fighter("fighter-many-fights")

    assert result is not None
    business_queries_10_fights = [
        q for q in counter.queries if not q.startswith("PRAGMA")
    ]

    event.remove(engine, "before_cursor_execute", counter.callback)

    # Reset and test with 20 fights
    fighter2 = Fighter(
        id="fighter-more-fights",
        name="Fighter with Even More Fights",
        division="Lightweight",
    )
    session.add(fighter2)

    for i in range(20):
        fight = Fight(
            id=f"fight-more-{i}",
            fighter_id="fighter-more-fights",
            opponent_name=f"Opponent {i}",
            event_name=f"UFC Event {i}",
            event_date=date(2024, 1, 1),
            result="win",
            method="KO/TKO",
            round=1,
            time="2:30",
        )
        session.add(fight)

    await session.commit()

    counter2 = QueryCounter()
    event.listen(engine, "before_cursor_execute", counter2.callback)

    result2 = await repo.get_fighter("fighter-more-fights")

    assert result2 is not None
    business_queries_20_fights = [
        q for q in counter2.queries if not q.startswith("PRAGMA")
    ]

    event.remove(engine, "before_cursor_execute", counter2.callback)

    # Query count should be the same regardless of fight count (no N+1)
    assert len(business_queries_10_fights) == len(business_queries_20_fights), (
        f"Query count should not scale with fights. "
        f"10 fights: {len(business_queries_10_fights)} queries, "
        f"20 fights: {len(business_queries_20_fights)} queries"
    )
