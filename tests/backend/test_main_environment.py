"""Tests covering runtime environment validation inside the FastAPI lifespan."""

from __future__ import annotations

import logging
from typing import Any

import pytest
from fastapi import FastAPI

import backend.main as backend_main


def _prepare_lifespan_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub heavyweight collaborators so the lifespan can run in isolation."""

    def _postgresql() -> str:
        """Return a deterministic non-SQLite database type."""

        return "postgresql"

    def _synthetic_database_url() -> str:
        """Return a fake database URL that exercises the sanitizer."""

        return "postgresql://tester:secret@example.com/ufc"

    async def _noop_async(*_: Any, **__: Any) -> None:
        """Provide an awaitable that does nothing (for warmup + teardown)."""

        return None

    monkeypatch.setattr(
        "backend.db.connection.get_database_type", _postgresql, raising=False
    )
    monkeypatch.setattr(
        "backend.db.connection.get_database_url", _synthetic_database_url, raising=False
    )
    monkeypatch.setattr("backend.warmup.warmup_all", _noop_async, raising=False)
    monkeypatch.setattr("backend.cache.close_redis", _noop_async, raising=False)


async def _run_lifespan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Execute the FastAPI lifespan context to trigger startup hooks."""

    _prepare_lifespan_dependencies(monkeypatch)
    app = FastAPI()
    async with backend_main.lifespan(app):
        # The context body is intentionally empty; entering and exiting the
        # lifespan is sufficient to trigger validation + cleanup hooks.
        pass


def _warning_messages(caplog: pytest.LogCaptureFixture) -> list[str]:
    """Return warning-level log messages produced by ``backend.main``."""

    return [
        record.getMessage()
        for record in caplog.records
        if record.levelno >= logging.WARNING and record.name == backend_main.logger.name
    ]


@pytest.mark.asyncio
async def test_lifespan_emits_warnings_when_optional_env_missing(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    request: pytest.FixtureRequest,
) -> None:
    """Ensure missing optional configuration surfaces explicit warnings."""

    _ = request  # Document the fixture dependency for the asyncio compatibility plugin.

    caplog.clear()
    caplog.set_level(logging.WARNING, backend_main.logger.name)

    # Remove optional environment variables to trigger the warning pathway.
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)

    await _run_lifespan(monkeypatch)

    messages = _warning_messages(caplog)
    assert any(
        "Environment Configuration Warnings" in message for message in messages
    ), "Expected missing optional config warnings to be logged."


@pytest.mark.asyncio
async def test_lifespan_suppresses_warnings_when_env_complete(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    request: pytest.FixtureRequest,
) -> None:
    """Ensure configured optional environment variables avoid spurious warnings."""

    _ = request  # Document the fixture dependency for the asyncio compatibility plugin.

    caplog.clear()
    caplog.set_level(logging.WARNING, backend_main.logger.name)

    # Provide realistic values so validation considers the configuration complete.
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://example.com")

    await _run_lifespan(monkeypatch)

    messages = _warning_messages(caplog)
    assert all(
        "Environment Configuration Warnings" not in message for message in messages
    ), "Did not expect optional configuration warnings when overrides are supplied."
