"""Unit tests covering the typed application settings implementation."""

from __future__ import annotations

import logging

import pytest

from backend.main import _validate_environment
from backend.settings import (
    DEFAULT_REDIS_URL,
    DEFAULT_SQLITE_DATABASE_URL,
    AppSettings,
)


def test_app_settings_sqlite_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Using ``use_sqlite`` should force the SQLite URL regardless of env state."""

    monkeypatch.delenv("DATABASE_URL", raising=False)
    configured = AppSettings(use_sqlite=True)

    assert configured.resolved_database_url == DEFAULT_SQLITE_DATABASE_URL
    assert configured.database_type == "sqlite"


def test_app_settings_postgres_conversion(monkeypatch: pytest.MonkeyPatch) -> None:
    """PostgreSQL URLs should normalize to the async psycopg dialect."""

    monkeypatch.delenv("USE_SQLITE", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/app")
    configured = AppSettings()

    assert (
        configured.resolved_database_url
        == "postgresql+psycopg://user:pass@localhost:5432/app"
    )
    assert configured.database_type == "postgresql"


def test_optional_config_warnings_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default configuration should warn when optional settings remain unset."""

    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    configured = AppSettings()

    warnings = configured.optional_config_warnings()

    assert any("REDIS_URL" in warning for warning in warnings)
    assert any("CORS_ALLOW_ORIGINS" in warning for warning in warnings)


def test_optional_config_warnings_clear_when_values_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Supplying overrides should suppress optional configuration warnings."""

    monkeypatch.setenv("REDIS_URL", DEFAULT_REDIS_URL)
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://example.com")
    configured = AppSettings()

    warnings = configured.optional_config_warnings()

    assert warnings == []


def test_validate_environment_logging(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The environment validator should emit warnings when optional inputs are absent."""

    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    candidate = AppSettings()

    with caplog.at_level(logging.WARNING):
        _validate_environment(active_settings=candidate)

    assert "REDIS_URL is not set" in caplog.text
    assert "CORS_ALLOW_ORIGINS is not set" in caplog.text


def test_validate_environment_silent_when_overrides_present(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Providing full configuration should avoid warning output."""

    monkeypatch.setenv("REDIS_URL", DEFAULT_REDIS_URL)
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://example.com")
    candidate = AppSettings()

    with caplog.at_level(logging.WARNING):
        _validate_environment(active_settings=candidate)

    assert "Environment Configuration Warnings" not in caplog.text
