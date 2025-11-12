"""Tests for the image validation API flag filtering endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from typing import Any, Final

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.api import image_validation
from backend.db.models import Base, Fighter


class _AsyncResultWrapper:
    """Lightweight adapter mimicking :class:`~sqlalchemy.ext.asyncio.AsyncResult`."""

    def __init__(self, result: Result[Any]) -> None:
        self._result = result

    def scalars(self):  # type: ignore[override]
        """Expose the scalar result helper from the wrapped synchronous result."""

        return self._result.scalars()

    def scalar_one(self) -> Any:
        """Return a single scalar from the underlying synchronous result set."""

        return self._result.scalar_one()


class _AsyncSessionFacade:
    """Minimal async-compatible shim around SQLAlchemy's synchronous session."""

    def __init__(self, sync_session: Session) -> None:
        self._sync_session = sync_session

    def add_all(self, instances: Iterable[Any]) -> None:
        """Delegate bulk addition of ORM instances to the synchronous session."""

        self._sync_session.add_all(list(instances))

    async def execute(self, statement: Any) -> _AsyncResultWrapper:
        """Execute ``statement`` synchronously and wrap the result for awaiters."""

        result = self._sync_session.execute(statement)
        return _AsyncResultWrapper(result)

    async def commit(self) -> None:
        """Flush and commit the pending transaction using the synchronous session."""

        self._sync_session.commit()

    async def rollback(self) -> None:
        """Rollback the underlying synchronous transaction if present."""

        self._sync_session.rollback()

    def in_transaction(self) -> bool:
        """Report whether the synchronous session currently holds a transaction."""

        return bool(self._sync_session.in_transaction())


@asynccontextmanager
async def in_memory_session() -> AsyncIterator[AsyncSession]:
    """Yield a fresh in-memory SQLite session with the schema initialised."""

    engine = create_engine("sqlite:///:memory:", future=True)
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as sync_session:
            async_session = _AsyncSessionFacade(sync_session)
            try:
                yield async_session  # type: ignore[return-value]
            finally:
                if async_session.in_transaction():
                    await async_session.rollback()
    finally:
        engine.dispose()


async def _seed_flagged_fighters(session: AsyncSession) -> None:
    """Populate the session with fighters carrying a mix of validation flags."""

    low_resolution_details: Final[dict[str, int]] = {"width": 320, "height": 240}

    fighters: list[Fighter] = [
        Fighter(
            id="flag-alpha",
            name="Alpha Flag",
            image_url="https://cdn.example.com/alpha.jpg",
            image_resolution_width=640,
            image_resolution_height=480,
            image_validation_flags={"low_resolution": low_resolution_details},
        ),
        Fighter(
            id="flag-beta",
            name="Beta Flag",
            image_validation_flags={"low_resolution": True, "multiple_faces": 2},
        ),
        Fighter(
            id="flag-gamma",
            name="Gamma Flag",
            image_validation_flags={"no_face_detected": True},
        ),
        Fighter(
            id="flag-delta",
            name="Delta Flag",
            image_validation_flags=None,
        ),
    ]

    session.add_all(fighters)
    await session.commit()


@pytest.mark.asyncio
async def test_get_fighters_by_flag_filters_via_database_predicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The API should delegate JSON flag filtering to the database layer."""

    monkeypatch.setattr(
        "backend.api.image_validation.db_connection.get_database_type",
        lambda: "sqlite",
    )

    async with in_memory_session() as session:
        await _seed_flagged_fighters(session)

        response = await image_validation.get_fighters_by_flag(
            flag="low_resolution",
            limit=10,
            offset=0,
            session=session,
        )

    assert response["total"] == 2
    assert response["count"] == 2
    assert response["limit"] == 10
    assert response["offset"] == 0
    assert [entry["name"] for entry in response["fighters"]] == [
        "Alpha Flag",
        "Beta Flag",
    ]
    assert response["fighters"][0]["flag_details"] == {"width": 320, "height": 240}
    assert response["fighters"][1]["flag_details"] is True


@pytest.mark.asyncio
async def test_get_fighters_by_flag_preserves_total_during_pagination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Paginated responses should expose the full result count alongside the slice."""

    monkeypatch.setattr(
        "backend.api.image_validation.db_connection.get_database_type",
        lambda: "sqlite",
    )

    async with in_memory_session() as session:
        await _seed_flagged_fighters(session)

        page = await image_validation.get_fighters_by_flag(
            flag="low_resolution",
            limit=1,
            offset=1,
            session=session,
        )

    assert page["total"] == 2
    assert page["count"] == 1
    assert page["limit"] == 1
    assert page["offset"] == 1
    assert [entry["name"] for entry in page["fighters"]] == ["Beta Flag"]
