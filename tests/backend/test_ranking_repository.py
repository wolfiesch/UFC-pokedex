from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date

import pytest

try:
    import pytest_asyncio
    from sqlalchemy.ext.asyncio import AsyncSession
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    pytest.skip(
        f"Optional dependency '{exc.name}' is required for ranking repository tests.",
        allow_module_level=True,
    )

from backend.db.models import Base, Fighter, FighterRanking
from backend.db.repositories.ranking_repository import RankingRepository
from tests.backend.postgres import (
    TemporaryPostgresSchema,
    postgres_schema,
)  # noqa: F401


@pytest_asyncio.fixture
async def session(
    postgres_schema: TemporaryPostgresSchema,
) -> AsyncIterator[AsyncSession]:
    """Provide an async session bound to a disposable PostgreSQL schema."""

    async with postgres_schema.session_scope(Base.metadata) as session:
        yield session


@pytest.mark.asyncio
async def test_get_peak_ranking_prefers_latest_snapshot_for_tied_rank(
    session: AsyncSession,
) -> None:
    """Tied peak ranks should return the most recent snapshot for determinism."""

    fighter = Fighter(id="fighter-1", name="Test Fighter")
    session.add(fighter)
    await session.flush()

    older_snapshot = FighterRanking(
        fighter_id=fighter.id,
        division="Lightweight",
        rank=3,
        previous_rank=4,
        rank_date=date(2024, 1, 1),
        source="ufc",
    )
    newer_snapshot = FighterRanking(
        fighter_id=fighter.id,
        division="Lightweight",
        rank=3,
        previous_rank=5,
        rank_date=date(2024, 4, 1),
        source="ufc",
    )
    session.add_all([older_snapshot, newer_snapshot])
    await session.commit()

    repo = RankingRepository(session)

    peak = await repo.get_peak_ranking(fighter.id, source="ufc")

    assert peak is not None
    assert peak["rank_date"] == date(2024, 4, 1)
    assert peak["peak_rank"] == 3
