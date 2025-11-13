"""Tests covering the image validation duplicate detection logic."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.image_validation import get_duplicate_images
from backend.db.models import Base, Fighter
from tests.backend.postgres import TemporaryPostgresSchema


class QueryCollector:
    """Collect executed SQL statements for later inspection."""

    def __init__(self) -> None:
        self.statements: list[str] = []

    def callback(
        self,
        conn,  # type: ignore[annotation-unchecked]
        cursor,
        statement: str,
        parameters,
        context,
        executemany,
    ) -> None:
        """Record the emitted SQL statement for assertion purposes."""

        self.statements.append(statement)


def _filter_business_queries(statements: list[str]) -> list[str]:
    """Return only the SELECT statements representing application work."""

    return [
        statement
        for statement in statements
        if statement.lstrip().upper().startswith("SELECT")
        and " FROM " in statement.upper().replace("\n", " ")
    ]


async def _seed_duplicate_data(session: AsyncSession) -> None:
    """Populate the database with fighters exhibiting duplicate flag patterns."""

    session.add_all(
        [
            Fighter(
                id="primary-1",
                name="Primary One",
                image_validation_flags={
                    "potential_duplicates": ["dup-1", "dup-2", "dup-3"]
                },
            ),
            Fighter(
                id="primary-2",
                name="Primary Two",
                image_validation_flags={
                    "potential_duplicates": ["dup-2", "dup-3", "missing"]
                },
            ),
            Fighter(id="dup-1", name="Duplicate One"),
            Fighter(id="dup-2", name="Duplicate Two"),
            Fighter(id="dup-3", name="Duplicate Three"),
        ]
    )
    await session.commit()


@pytest.mark.asyncio
async def test_get_duplicate_images_uses_single_lookup_query(
    monkeypatch: pytest.MonkeyPatch,
    postgres_schema: TemporaryPostgresSchema,
) -> None:
    """Verify duplicate lookup executes exactly one consolidated query regardless of size."""

    postgres_schema.install_as_default(monkeypatch)

    async with postgres_schema.session_scope(Base.metadata) as session:
        await _seed_duplicate_data(session)

        collector = QueryCollector()
        engine = session.bind
        assert engine is not None, "AsyncSession should be bound to an engine"
        sync_engine = engine.sync_engine
        event.listen(sync_engine, "before_cursor_execute", collector.callback)
        try:
            response: dict[str, Any] = await get_duplicate_images(
                limit=10, offset=0, session=session
            )
        finally:
            event.remove(sync_engine, "before_cursor_execute", collector.callback)

    business_queries = _filter_business_queries(collector.statements)
    assert (
        len(business_queries) == 2
    ), f"Expected two SELECTs (fighters + lookup); saw: {business_queries}"

    assert response["count"] == 2
    first_entry = response["fighters"][0]
    second_entry = response["fighters"][1]

    assert [dup["name"] for dup in first_entry["duplicates"]] == [
        "Duplicate One",
        "Duplicate Two",
        "Duplicate Three",
    ]
    assert [dup["name"] for dup in second_entry["duplicates"]] == [
        "Duplicate Two",
        "Duplicate Three",
        "Unknown Fighter",
    ]
