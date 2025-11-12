"""Regression tests for backend warmup routines."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable
from typing import Any
from unittest.mock import AsyncMock

import pytest

import backend.warmup as warmup


class _DummyTransaction:
    """Test helper providing an async context manager that captures executions."""

    def __init__(self) -> None:
        self.connection: AsyncMock = AsyncMock()

    async def __aenter__(self) -> AsyncMock:
        """Return the mocked connection when entering the context manager."""

        return self.connection

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> bool:
        """Ensure the context manager suppresses no exceptions during teardown."""

        return False


def _generate_session(session: AsyncMock) -> AsyncIterator[AsyncMock]:
    """Yield a single mocked SQLAlchemy session for warmup iteration."""

    async def _iterator() -> AsyncIterator[AsyncMock]:
        yield session

    return _iterator()


@pytest.mark.asyncio
async def test_warmup_database_postgresql_executes_ping(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    """Ensure PostgreSQL warmup performs the SELECT 1 ping without warnings."""

    del request  # Fixture consumed to satisfy the custom asyncio harness.

    caplog.set_level(logging.INFO)

    dummy_txn = _DummyTransaction()

    # Patch the transaction helper so the warmup interacts with our dummy context.
    monkeypatch.setattr(warmup, "begin_engine_transaction", lambda engine: dummy_txn)

    await warmup.warmup_database(
        resolve_db_type=lambda: "postgresql",
        resolve_engine=lambda: object(),
    )

    assert dummy_txn.connection.execute.await_count == 1
    executed_statement = dummy_txn.connection.execute.await_args.args[0]
    assert str(executed_statement).strip().upper() == "SELECT 1"
    assert not [
        record for record in caplog.records if record.levelno >= logging.WARNING
    ]


@pytest.mark.asyncio
async def test_warmup_database_sqlite_skips_ping(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    """Verify SQLite warmup logs a skip message and avoids the ping."""

    del request  # Fixture consumed to satisfy the custom asyncio harness.

    caplog.set_level(logging.INFO)

    # Guard against accidental context manager usage by raising if called.
    def _fail_if_used(_: object) -> Awaitable[None]:
        raise AssertionError("SQLite warmup should not open pooled transactions")

    monkeypatch.setattr(warmup, "begin_engine_transaction", _fail_if_used)

    await warmup.warmup_database(resolve_db_type=lambda: "sqlite")

    assert any("skipped" in record.getMessage() for record in caplog.records)
    assert not [
        record for record in caplog.records if record.levelno >= logging.WARNING
    ]


@pytest.mark.asyncio
async def test_warmup_repository_queries_postgresql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirm PostgreSQL warmup exercises the repository list query."""

    session = AsyncMock()
    repo_instance = AsyncMock()

    monkeypatch.setattr(
        "backend.db.connection.get_db", lambda: _generate_session(session)
    )
    monkeypatch.setattr(
        "backend.db.repositories.PostgreSQLFighterRepository",
        lambda db_session: repo_instance,
    )

    await warmup.warmup_repository_queries(resolve_db_type=lambda: "postgresql")

    repo_instance.list_fighters.assert_awaited_once_with(limit=1, offset=0)
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_warmup_repository_queries_sqlite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate SQLite warmup performs a lightweight ORM select."""

    session = AsyncMock()

    monkeypatch.setattr(
        "backend.db.connection.get_db", lambda: _generate_session(session)
    )

    # Ensure the PostgreSQL repository is never instantiated for SQLite paths.
    def _fail_repo(_: Any) -> None:
        raise AssertionError("SQLite warmup should not build PostgreSQL repositories")

    monkeypatch.setattr(
        "backend.db.repositories.PostgreSQLFighterRepository", _fail_repo
    )

    await warmup.warmup_repository_queries(resolve_db_type=lambda: "sqlite")

    session.execute.assert_awaited()
