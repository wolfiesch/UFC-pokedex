"""Tests for database initialization, preflight checks, and seed safety."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.db.connection import get_database_type, get_database_url
from backend.scripts.seed_fighters import (
    check_sqlite_production_seed_safety,
    is_production_seed_data,
)


class TestDatabaseType:
    """Test database type detection."""

    def test_get_database_type_missing_database_url(self, monkeypatch) -> None:
        """Raise ``RuntimeError`` when ``DATABASE_URL`` is not configured."""

        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(RuntimeError) as exc_info:
            get_database_type()

        assert "DATABASE_URL is not set" in str(exc_info.value)

    def test_get_database_type_rejects_non_postgres_url(self, monkeypatch) -> None:
        """Raise when configuration points at a non-PostgreSQL backend."""

        monkeypatch.setenv("DATABASE_URL", "mysql://user:pass@localhost/db")

        with pytest.raises(RuntimeError) as exc_info:
            get_database_type()

        assert "PostgreSQL" in str(exc_info.value)

    def test_get_database_type_postgresql(self, monkeypatch) -> None:
        """Return ``postgresql`` for valid PostgreSQL connection strings."""

        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://user:pass@localhost/db",
        )

        assert get_database_type() == "postgresql"


class TestDatabaseURL:
    """Test database URL construction and sanitization."""

    def test_get_database_url_missing_env(self, monkeypatch) -> None:
        """Raise when ``DATABASE_URL`` is absent."""

        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(RuntimeError) as exc_info:
            get_database_url()

        assert "DATABASE_URL is not set" in str(exc_info.value)

    def test_get_database_url_rejects_non_postgres(self, monkeypatch) -> None:
        """Reject non-PostgreSQL URLs with a helpful error message."""

        monkeypatch.setenv("DATABASE_URL", "mysql://user:pass@localhost/db")

        with pytest.raises(RuntimeError) as exc_info:
            get_database_url()

        assert "PostgreSQL" in str(exc_info.value)

    def test_get_database_url_normalizes_postgres_scheme(self, monkeypatch) -> None:
        """Normalize legacy ``postgres://`` URLs for SQLAlchemy."""

        monkeypatch.setenv(
            "DATABASE_URL",
            "postgres://user:pass@localhost:5432/db",
        )

        assert get_database_url() == "postgresql+psycopg://user:pass@localhost:5432/db"


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
                "postgresql+psycopg://user@localhost/db",
                "postgresql+psycopg://user@localhost/db",
            ),
            (
                "postgresql+psycopg://:@localhost/db",
                "postgresql+psycopg://:***@localhost/db",
            ),
            (
                "postgresql+psycopg://localhost/db",
                "postgresql+psycopg://localhost/db",
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


class TestSeedSafetyCheck:
    """Test production seed safety checks enforce PostgreSQL usage."""

    def test_requires_postgresql_backend(self) -> None:
        """Block seeding when a non-PostgreSQL backend is detected."""

        path = Path("data/processed/fighters_list.jsonl")

        with pytest.raises(RuntimeError) as exc_info:
            check_sqlite_production_seed_safety("sqlite", path)

        assert "PostgreSQL" in str(exc_info.value)

    def test_allows_postgresql_with_any_data(self) -> None:
        """Permit all data sources once PostgreSQL is in use."""

        path = Path("data/processed/fighters_list.jsonl")

        assert check_sqlite_production_seed_safety("postgresql", path) is True


class TestDatabaseInitialization:
    """Test that tables are created correctly based on database type."""

    @pytest.mark.asyncio
    @patch("backend.main.get_database_url")
    @patch("backend.main.get_database_type")
    async def test_startup_rejects_non_postgres_backend(
        self, mock_get_type, mock_get_url
    ) -> None:
        """Ensure lifespan hook raises when the backend is not PostgreSQL."""

        mock_get_type.return_value = "sqlite"
        mock_get_url.return_value = "postgresql+psycopg://user:pass@localhost/db"

        from fastapi import FastAPI

        from backend.main import lifespan

        app = FastAPI()

        with pytest.raises(RuntimeError) as exc_info:
            async with lifespan(app):
                pass

        assert "Unsupported database type" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("backend.warmup.warmup_all", new_callable=AsyncMock)
    @patch("backend.main.get_database_url")
    @patch("backend.main.get_database_type")
    @patch("backend.main.get_engine")
    async def test_postgresql_skips_create_all(
        self, mock_get_engine, mock_get_type, mock_get_url, mock_warmup
    ) -> None:
        """Test that PostgreSQL mode does NOT call create_all()."""
        mock_get_type.return_value = "postgresql"
        mock_get_url.return_value = "postgresql+psycopg://user:pass@localhost/db"

        # Import and run lifespan
        from fastapi import FastAPI

        from backend.main import lifespan

        app = FastAPI()

        async with lifespan(app):
            pass

        # Verify that warmup delegated engine resolution without triggering create_all.
        mock_warmup.assert_awaited_once()
        awaited_call = mock_warmup.await_args
        assert awaited_call is not None
        assert awaited_call.kwargs.get("resolve_engine") is mock_get_engine

    @patch("backend.scripts.seed_fighters.get_database_type")
    @patch("backend.scripts.seed_fighters.get_engine")
    async def test_seed_script_skips_create_all_for_postgresql(
        self, mock_get_engine, mock_get_type
    ):
        """Test that seed script does NOT call create_all() for PostgreSQL."""
        from backend.scripts.seed_fighters import ensure_tables

        mock_get_type.return_value = "postgresql"

        # Run ensure_tables
        await ensure_tables()

        # Verify that get_engine was NOT called
        mock_get_engine.assert_not_called()

    @pytest.mark.asyncio
    @patch("backend.scripts.seed_fighters.get_database_type")
    async def test_seed_script_raises_for_non_postgres_backend(
        self, mock_get_type
    ) -> None:
        """Ensure seed helpers surface clear guidance for unsupported engines."""

        from backend.scripts.seed_fighters import ensure_tables

        mock_get_type.return_value = "sqlite"

        with pytest.raises(RuntimeError) as exc_info:
            await ensure_tables()

        assert "PostgreSQL" in str(exc_info.value)
