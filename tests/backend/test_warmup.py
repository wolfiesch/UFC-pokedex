"""Regression tests for backend warmup routines."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
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
    sentinel_engine = object()

    # Patch the transaction helper so the warmup interacts with our dummy context
    # and capture the engine argument for verification.
    captured_engines: list[object] = []

    def _capture_engine(engine: object) -> _DummyTransaction:
        captured_engines.append(engine)
        return dummy_txn

    monkeypatch.setattr(warmup, "begin_engine_transaction", _capture_engine)

    await warmup.warmup_database(
        resolve_db_type=lambda: "postgresql",
        resolve_engine=lambda: sentinel_engine,
    )

    assert captured_engines == [sentinel_engine]
    assert dummy_txn.connection.execute.await_count == 1
    executed_statement = dummy_txn.connection.execute.await_args.args[0]
    assert str(executed_statement).strip().upper() == "SELECT 1"
    assert not [
        record for record in caplog.records if record.levelno >= logging.WARNING
    ]


@pytest.mark.asyncio
async def test_warmup_database_warns_on_non_postgres(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    """Verify non-PostgreSQL backends still execute the ping while logging a warning."""

    del request  # Fixture consumed to satisfy the custom asyncio harness.

    caplog.set_level(logging.INFO)

    dummy_txn = _DummyTransaction()
    sentinel_engine = object()

    monkeypatch.setattr(warmup, "begin_engine_transaction", lambda _: dummy_txn)

    await warmup.warmup_database(
        resolve_db_type=lambda: "sqlite",
        resolve_engine=lambda: sentinel_engine,
    )

    assert dummy_txn.connection.execute.await_count == 1
    assert any(
        "expected PostgreSQL" in record.getMessage() for record in caplog.records
    )


@pytest.mark.asyncio
async def test_warmup_repository_queries_postgresql(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    """Confirm PostgreSQL warmup exercises the repository list query."""

    del request

    caplog.set_level(logging.INFO)

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
    assert not [
        record for record in caplog.records if record.levelno >= logging.WARNING
    ]


@pytest.mark.asyncio
async def test_warmup_repository_queries_warns_on_non_postgres(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    """Validate non-PostgreSQL backends still issue the repository warmup with a warning."""

    del request

    caplog.set_level(logging.INFO)

    session = AsyncMock()
    repo_instance = AsyncMock()

    monkeypatch.setattr(
        "backend.db.connection.get_db", lambda: _generate_session(session)
    )
    monkeypatch.setattr(
        "backend.db.repositories.PostgreSQLFighterRepository",
        lambda db_session: repo_instance,
    )

    await warmup.warmup_repository_queries(resolve_db_type=lambda: "sqlite")

    repo_instance.list_fighters.assert_awaited_once_with(limit=1, offset=0)
    assert any(
        "expected PostgreSQL" in record.getMessage() for record in caplog.records
    )
