"""Tests for database initialization, preflight checks, and seed safety."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.db.connection import get_database_type, get_database_url
from backend.scripts.seed_fighters import is_production_seed_data


class TestDatabaseType:
    """Test database type detection."""

    def test_get_database_type_postgresql(self, monkeypatch):
        """PostgreSQL URLs should successfully return the backend type."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+psycopg://ufc_reader:pass@localhost:5432/pokedex",
        )

        assert get_database_type() == "postgresql"

    def test_get_database_type_missing_database_url_raises(self, monkeypatch):
        """Missing DATABASE_URL must fail fast with a descriptive error."""
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(RuntimeError) as exc_info:
            get_database_type()

        assert "DATABASE_URL is not set" in str(exc_info.value)

    def test_get_database_type_rejects_non_postgres_urls(self, monkeypatch):
        """Non-PostgreSQL URLs should trigger a RuntimeError."""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp/app.db")

        with pytest.raises(RuntimeError) as exc_info:
            get_database_type()

        # The validation helper now enforces PostgreSQL-specific schemes.
        assert "PostgreSQL" in str(exc_info.value)


class TestDatabaseURL:
    """Test database URL construction and sanitization."""

    def test_get_database_url_postgresql_passthrough(self, monkeypatch):
        """Already-normalized PostgreSQL URLs should round-trip unchanged."""
        pg_url = "postgresql+psycopg://user:pass@localhost/db"
        monkeypatch.setenv("DATABASE_URL", pg_url)

        assert get_database_url() == pg_url

    def test_get_database_url_upgrades_legacy_scheme(self, monkeypatch):
        """Legacy postgres:// URLs should be normalized to psycopg syntax."""
        monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/dbname")

        assert (
            get_database_url() == "postgresql+psycopg://user:pass@localhost:5432/dbname"
        )

    def test_get_database_url_missing_env_var_raises(self, monkeypatch):
        """Missing DATABASE_URL should raise a RuntimeError."""
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(RuntimeError) as exc_info:
            get_database_url()

        assert "DATABASE_URL is not set" in str(exc_info.value)


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
                "postgresql+psycopg://readonly@localhost/db",
                "postgresql+psycopg://readonly@localhost/db",
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


class TestDatabaseInitialization:
    """Test that tables are created correctly based on database type."""

    @pytest.mark.asyncio
    @patch("backend.warmup.warmup_all", new_callable=AsyncMock)
    @patch("backend.main.get_database_type")
    @patch("backend.main.get_database_url")
    @patch("backend.main.get_engine")
    async def test_postgresql_skips_create_all(
        self,
        mock_get_engine,
        mock_get_database_url,
        mock_get_type,
        mock_warmup,
    ) -> None:
        """Test that PostgreSQL mode does NOT call create_all()."""
        mock_get_type.return_value = "postgresql"
        mock_get_database_url.return_value = (
            "postgresql+psycopg://api:secret@localhost:5432/ufc"
        )

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
    async def test_seed_script_creates_tables_for_sqlite(
        self, mock_get_engine, mock_get_type
    ):
        """Test that seed script calls create_all() for SQLite."""
        from backend.scripts.seed_fighters import ensure_tables

        mock_get_type.return_value = "sqlite"

        # Mock engine and connection
        mock_conn = AsyncMock()
        mock_engine = MagicMock()
        mock_engine.begin = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_get_engine.return_value = mock_engine

        # Run ensure_tables
        await ensure_tables()

        # Verify that run_sync (which calls create_all) was called
        mock_conn.run_sync.assert_called_once()

    @pytest.mark.asyncio
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
    @patch("backend.main.get_database_type")
    @patch("backend.main.get_database_url")
    async def test_lifespan_raises_for_non_postgres_backends(
        self, mock_get_database_url, mock_get_type
    ) -> None:
        """FastAPI lifespan should crash if the backend is not PostgreSQL."""
        from fastapi import FastAPI

        from backend.main import lifespan

        mock_get_type.return_value = "sqlite"
        mock_get_database_url.return_value = "sqlite:///tmp/app.db"

        app = FastAPI()

        with pytest.raises(RuntimeError) as exc_info:
            async with lifespan(app):
                pass

        assert "Unsupported database type" in str(exc_info.value)
