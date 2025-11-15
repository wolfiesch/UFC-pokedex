from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, timedelta

import pytest

try:
    import pytest_asyncio
    from sqlalchemy.ext.asyncio import AsyncSession
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    pytest.skip(
        f"Optional dependency '{exc.name}' is required for fighter fight status tests.",
        allow_module_level=True,
    )

from backend.db.models import Base, Event, Fight, Fighter
from backend.db.repositories.fighter import FighterRepository
from tests.backend.postgres import (
    TemporaryPostgresSchema,
    postgres_schema,
)  # noqa: F401


@pytest_asyncio.fixture
async def session(
    postgres_schema: TemporaryPostgresSchema,
) -> AsyncIterator[AsyncSession]:
    """Provide an async session scoped to a disposable PostgreSQL schema."""

    async with postgres_schema.session_scope(Base.metadata) as session:
        yield session


@pytest.mark.asyncio
async def test_fetch_fight_status_surfaces_next_fight_for_both_sides(
    session: AsyncSession,
) -> None:
    """Upcoming fights must populate ``next_fight_date`` for both fighters."""

    future_event_date = date.today() + timedelta(days=30)

    arman = Fighter(id="fighter-arman", name="Arman Tsarukyan")
    hooker = Fighter(id="fighter-hooker", name="Dan Hooker")
    event = Event(
        id="event-tsarukyan-hooker",
        name="UFC Austin",
        date=future_event_date,
        status="upcoming",
    )
    fight_one = Fight(
        id="tsarukyan-hooker",
        fighter_id=arman.id,
        opponent_id=hooker.id,
        opponent_name=hooker.name,
        event_id=event.id,
        event_name=event.name,
        event_date=future_event_date,
        result="next",
    )
    fight_two = Fight(
        id="tsarukyan-hooker-opp",
        fighter_id=hooker.id,
        opponent_id=arman.id,
        opponent_name=arman.name,
        event_id=event.id,
        event_name=event.name,
        event_date=future_event_date,
        result="next",
    )

    session.add_all([arman, hooker, event, fight_one, fight_two])
    await session.commit()

    repo = FighterRepository(session)
    statuses = await repo._fetch_fight_status([arman.id, hooker.id])

    assert statuses[arman.id]["next_fight_date"] == future_event_date
    assert statuses[hooker.id]["next_fight_date"] == future_event_date
