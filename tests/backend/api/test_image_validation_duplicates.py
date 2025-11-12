"""Tests for duplicate image API query behavior."""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.api.image_validation import get_duplicate_images
from backend.db.models import Base, Fighter


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
        and not statement.lstrip().upper().startswith("SELECT CAST(")
    ]


async def _run_duplicate_query_assertion() -> None:
    """Exercise ``get_duplicate_images`` and validate query usage."""

    engine: AsyncEngine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", future=True
    )
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            engine, expire_on_commit=False
        )

        async with session_factory() as session:
            # Seed fighters with duplicate relationships. Multiple entries point to the
            # same duplicate set to ensure the implementation stays constant time relative
            # to the number of duplicates returned.
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

            collector = QueryCollector()
            engine_bind = session.bind
            assert engine_bind is not None, "AsyncSession should be bound to an engine"
            sync_engine = engine_bind.sync_engine
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
    finally:
        await engine.dispose()


def test_get_duplicate_images_uses_single_lookup_query() -> None:
    """Verify duplicate lookup executes exactly one consolidated query regardless of size."""

    # ``pytest_asyncio`` is optional in the kata environment. Running the coroutine via
    # :func:`asyncio.run` keeps the test compatible with both the fallback runner and the
    # real plugin when present.
    asyncio.run(_run_duplicate_query_assertion())
