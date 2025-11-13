"""Tests for the image validation API flag filtering endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Final

import pytest
from sqlalchemy import cast, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.api import image_validation
from backend.db import connection as db_connection
from backend.db.models import Base, Fighter
from tests.backend.postgres import TemporaryPostgresSchema


@asynccontextmanager
async def _session_scope(
    schema: TemporaryPostgresSchema,
) -> AsyncIterator[AsyncSession]:
    """Yield an :class:`AsyncSession` bound to a dedicated PostgreSQL schema."""

    engine = schema.create_async_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()

    await engine.dispose()


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
    postgres_schema: TemporaryPostgresSchema,
) -> None:
    """The API should delegate JSON flag filtering to the database layer."""

    postgres_schema.install_as_default(monkeypatch)
    monkeypatch.setattr(image_validation, "db_connection", db_connection, raising=False)
    monkeypatch.setattr(
        image_validation,
        "_build_flag_predicate",
        lambda flag: func.jsonb_exists(
            cast(Fighter.image_validation_flags, JSONB), flag
        ),
        raising=False,
    )

    async with _session_scope(postgres_schema) as session:
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
    postgres_schema: TemporaryPostgresSchema,
) -> None:
    """Paginated responses should expose the full result count alongside the slice."""

    postgres_schema.install_as_default(monkeypatch)
    monkeypatch.setattr(image_validation, "db_connection", db_connection, raising=False)
    monkeypatch.setattr(
        image_validation,
        "_build_flag_predicate",
        lambda flag: func.jsonb_exists(
            cast(Fighter.image_validation_flags, JSONB), flag
        ),
        raising=False,
    )

    async with _session_scope(postgres_schema) as session:
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
