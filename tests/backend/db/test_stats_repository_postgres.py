"""PostgreSQL-specific unit tests for :mod:`backend.db.repositories.stats_repository`."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import ColumnElement

from backend.db.repositories.stats_repository import StatsRepository


def _compile_expression(expression: ColumnElement[Any]) -> str:
    """Compile a SQLAlchemy expression with the PostgreSQL dialect for inspection."""

    compiled = expression.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    )
    return str(compiled)


@pytest.mark.asyncio
async def test_fight_duration_expression_uses_split_part() -> None:
    """The duration helper should rely on PostgreSQL's ``split_part`` function."""

    repository = StatsRepository(AsyncMock())
    expression = repository._fight_duration_seconds_expression()
    compiled = _compile_expression(expression).lower()

    assert "split_part" in compiled


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("bucket", "expected_token"),
    (
        ("year", "'year'"),
        ("quarter", "'quarter'"),
        ("month", "'month'"),
    ),
)
async def test_bucket_start_expression_relies_on_date_trunc(
    bucket: str,
    expected_token: str,
) -> None:
    """Bucket helpers should call PostgreSQL ``date_trunc`` with the appropriate unit."""

    repository = StatsRepository(AsyncMock())
    expression = repository._bucket_start_expression(bucket)
    compiled = _compile_expression(expression).lower()

    assert "date_trunc" in compiled
    assert expected_token in compiled
