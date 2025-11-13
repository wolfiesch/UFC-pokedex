"""Tests for database connection leak prevention."""

import pytest
from sqlalchemy.exc import SQLAlchemyError

from backend.db import connection as db_connection
from backend.db.connection import get_db
from backend.db.models import Base
from tests.backend.postgres import TemporaryPostgresSchema


@pytest.mark.asyncio
async def test_session_closes_on_commit_error(
    postgres_schema: TemporaryPostgresSchema,
    monkeypatch: pytest.MonkeyPatch,
):
    """Test that session is properly closed even if commit fails."""
    postgres_schema.install_as_default(monkeypatch)

    async def _prepare_schema() -> None:
        async with postgres_schema.session_scope(Base.metadata):
            pass

    await _prepare_schema()
    monkeypatch.setattr(db_connection, "_engine", None, raising=False)
    monkeypatch.setattr(db_connection, "_session_factory", None, raising=False)
    session_gen = get_db()
    session = await anext(session_gen)

    # Track if close was called
    close_called = False
    original_close = session.close

    async def tracked_close():
        nonlocal close_called
        close_called = True
        await original_close()

    session.close = tracked_close

    # Mock commit to fail
    async def failing_commit():
        raise SQLAlchemyError("Simulated commit failure")

    session.commit = failing_commit

    # Simulate commit failure by triggering cleanup
    with pytest.raises(SQLAlchemyError):
        try:
            await anext(session_gen)
        except StopAsyncIteration:
            pass

    assert close_called, "Session close() should be called even on commit error"
