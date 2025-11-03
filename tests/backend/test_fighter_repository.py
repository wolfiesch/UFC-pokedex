from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
pytest.importorskip("sqlalchemy")
pytest.importorskip("pytest_asyncio")

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
