"""Tests for database initialization, preflight checks, and seed safety."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from backend.db.connection import get_database_type, get_database_url
from backend.scripts.seed_fighters import (
    ensure_postgresql_backend,
    is_production_seed_data,
)


class TestDatabaseType:
    """Validate the enforced PostgreSQL-only database configuration."""

    def test_get_database_type_requires_database_url(self, monkeypatch):
        """DATABASE_URL must be provided; missing configuration raises immediately."""

        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(RuntimeError):
            get_database_type()

    def test_get_database_type_rejects_non_postgres(self, monkeypatch):
        """Non-PostgreSQL URLs are rejected with a descriptive error message."""

        monkeypatch.setenv("DATABASE_URL", "mysql://user:pass@localhost/db")

        with pytest.raises(RuntimeError) as exc_info:
            get_database_type()

        assert "PostgreSQL" in str(exc_info.value)

    def test_get_database_type_postgresql(self, monkeypatch):
        """Valid PostgreSQL URLs resolve to the canonical identifier."""

        monkeypatch.setenv(
            "DATABASE_URL", "postgresql+psycopg://user:pass@localhost/db"
        )

        assert get_database_type() == "postgresql"


class TestDatabaseURL:
    """Test database URL validation and normalization."""

    def test_get_database_url_requires_value(self, monkeypatch):
        """Missing DATABASE_URL triggers an instructive runtime error."""

        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(RuntimeError):
            get_database_url()

    def test_get_database_url_normalizes_postgres_scheme(self, monkeypatch):
        """Legacy ``postgresql://`` URLs are normalized to the async driver form."""

        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")

        assert get_database_url() == "postgresql+psycopg://user:pass@localhost/db"

    def test_get_database_url_rejects_non_postgres(self, monkeypatch):
        """Non-PostgreSQL schemes are rejected to avoid unsupported engines."""

        monkeypatch.setenv("DATABASE_URL", "mysql://user:pass@localhost/db")

        with pytest.raises(RuntimeError) as exc_info:
            get_database_url()

        assert "PostgreSQL" in str(exc_info.value)


class TestPreflightLogging:
    """Test startup preflight logging."""

    @patch("backend.main.get_database_type")
    @patch("backend.main.get_database_url")
    def test_sanitize_database_url_hides_password(self, mock_get_url, mock_get_type):
        """Test that database URL passwords are hidden in logs."""
        from backend.main import _sanitize_database_url

        test_cases = [
            (
                "postgresql+psycopg://user:secret123@localhost/db",
                "postgresql+psycopg://user:***@localhost/db",
            ),
            (
                "sqlite+aiosqlite:///./data/app.db",
                "sqlite+aiosqlite:///./data/app.db",
            ),
            (
                "postgresql+psycopg://user@localhost/db",
                "postgresql+psycopg://user@localhost/db",
            ),
        ]

        for input_url, expected_output in test_cases:
            assert _sanitize_database_url(input_url) == expected_output


class TestSeedProductionDataDetection:
    """Test detection of production vs sample seed data."""

    def test_is_production_seed_data_detects_processed_dir(self):
        """Test that data/processed/ paths are detected as production."""
        path = Path("data/processed/fighters_list.jsonl")
        assert is_production_seed_data(path) is True

    def test_is_production_seed_data_detects_fighters_list(self):
        """Test that fighters_list.jsonl is detected as production."""
        path = Path("/some/path/fighters_list.jsonl")
        assert is_production_seed_data(path) is True

    def test_is_production_seed_data_fixtures_not_production(self):
        """Test that data/fixtures/ paths are NOT production."""
        path = Path("data/fixtures/fighters.jsonl")
        assert is_production_seed_data(path) is False

    def test_is_production_seed_data_other_paths_not_production(self):
        """Test that random paths are NOT production."""
        path = Path("data/sample.jsonl")
        assert is_production_seed_data(path) is False


class TestSeedBackendValidation:
    """Validate the streamlined PostgreSQL-only fighter seeding flow."""

    def test_ensure_postgresql_backend_accepts_postgres(self):
        """Explicit PostgreSQL identifiers pass validation without error."""

        ensure_postgresql_backend(db_type="postgresql")

    def test_ensure_postgresql_backend_rejects_non_postgres(self):
        """Any non-PostgreSQL identifier results in a descriptive runtime error."""

        with pytest.raises(RuntimeError) as exc_info:
            ensure_postgresql_backend(db_type="sqlite")

        assert "PostgreSQL" in str(exc_info.value)


class TestDatabaseInitialization:
    """Validate FastAPI lifespan behavior under the PostgreSQL-only contract."""

    @pytest.mark.asyncio
    @patch("backend.main.get_database_url")
    @patch("backend.main.get_database_type")
    async def test_lifespan_rejects_non_postgres(
        self, mock_get_type, mock_get_url
    ) -> None:
        """A non-PostgreSQL backend aborts startup with a clear runtime error."""

        mock_get_type.return_value = "mysql"
        mock_get_url.return_value = "mysql://user:pass@localhost/db"

        from fastapi import FastAPI

        from backend.main import lifespan

        app = FastAPI()

        with pytest.raises(RuntimeError):
            async with lifespan(app):
                pass

    @pytest.mark.asyncio
    @patch("backend.warmup.warmup_all", new_callable=AsyncMock)
    @patch("backend.main.get_database_url")
    @patch("backend.main.get_database_type")
    @patch("backend.main.get_engine")
    async def test_postgresql_invokes_warmup(
        self,
        mock_get_engine,
        mock_get_type,
        mock_get_url,
        mock_warmup,
    ) -> None:
        """PostgreSQL startup triggers the warmup routine with expected dependencies."""

        mock_get_type.return_value = "postgresql"
        mock_get_url.return_value = "postgresql+psycopg://user:pass@localhost/db"

        from fastapi import FastAPI

        from backend.main import lifespan

        app = FastAPI()

        async with lifespan(app):
            pass

        mock_warmup.assert_awaited_once()
        awaited_call = mock_warmup.await_args
        assert awaited_call is not None
        assert awaited_call.kwargs.get("resolve_engine") is mock_get_engine

        from backend import main as backend_main

        assert (
            awaited_call.kwargs.get("resolve_db_type") is backend_main.get_database_type
        )
