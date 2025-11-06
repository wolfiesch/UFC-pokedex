"""Tests for database connection leak prevention."""
import pytest
from sqlalchemy.exc import SQLAlchemyError
from backend.db.connection import get_db


@pytest.mark.asyncio
async def test_session_closes_on_commit_error():
    """Test that session is properly closed even if commit fails."""
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
    original_commit = session.commit

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
