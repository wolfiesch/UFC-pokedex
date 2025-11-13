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

    def test_get_database_type_postgresql(self, monkeypatch):
        """PostgreSQL URLs are accepted and reported correctly."""

        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://user:pass@localhost/db",
        )

        assert get_database_type() == "postgresql"

    def test_get_database_type_rejects_non_postgres(self, monkeypatch):
        """Non-PostgreSQL URLs cause an explicit startup failure."""

        monkeypatch.setenv("DATABASE_URL", "mysql://user:pass@localhost/db")

        with pytest.raises(RuntimeError):
            get_database_type()


class TestDatabaseURL:
    """Test database URL construction and validation."""

    def test_get_database_url_postgresql(self, monkeypatch):
        """PostgreSQL URLs are normalized to the async psycopg dialect."""

        monkeypatch.setenv(
            "DATABASE_URL",
            "postgres://user:pass@localhost/db",
        )

        url = get_database_url()
        assert url == "postgresql+psycopg://user:pass@localhost/db"

    def test_get_database_url_missing_env_raises(self, monkeypatch):
        """Missing DATABASE_URL causes a clear runtime error."""

        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(RuntimeError):
            get_database_url()

    def test_get_database_url_blank_env_raises(self, monkeypatch):
        """Blank DATABASE_URL values are rejected with guidance."""

        monkeypatch.setenv("DATABASE_URL", "   ")

        with pytest.raises(RuntimeError):
            get_database_url()

    def test_get_database_url_invalid_scheme_raises(self, monkeypatch):
        """Only PostgreSQL URLs are permitted."""

        monkeypatch.setenv("DATABASE_URL", "mysql://user:pass@localhost/db")

        with pytest.raises(RuntimeError):
            get_database_url()


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
    """Test production seed safety checks for SQLite."""

    def test_allows_postgresql_with_any_data(self):
        """Test that PostgreSQL allows any data source."""
        path = Path("data/processed/fighters_list.jsonl")
        # Should not raise, should return True
        assert check_sqlite_production_seed_safety("postgresql", path) is True

    def test_allows_sqlite_with_sample_data(self):
        """Test that SQLite allows sample/fixture data."""
        path = Path("data/fixtures/fighters.jsonl")
        assert check_sqlite_production_seed_safety("sqlite", path) is True

    def test_blocks_sqlite_with_production_data(self, monkeypatch):
        """Test that SQLite blocks production data without override."""
        monkeypatch.delenv("ALLOW_SQLITE_PROD_SEED", raising=False)
        path = Path("data/processed/fighters_list.jsonl")

        with pytest.raises(SystemExit) as exc_info:
            check_sqlite_production_seed_safety("sqlite", path)

        assert exc_info.value.code == 1

    def test_allows_sqlite_with_override_env_var(self, monkeypatch, capsys):
        """Test that ALLOW_SQLITE_PROD_SEED=1 allows production data on SQLite."""
        monkeypatch.setenv("ALLOW_SQLITE_PROD_SEED", "1")
        path = Path("data/processed/fighters_list.jsonl")

        # Should not raise, should return True
        result = check_sqlite_production_seed_safety("sqlite", path)
        assert result is True

        # Should print warning
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "ALLOW_SQLITE_PROD_SEED=1" in captured.out

    def test_blocks_sqlite_with_wrong_override_value(self, monkeypatch):
        """Test that ALLOW_SQLITE_PROD_SEED=0 does NOT allow production data."""
        monkeypatch.setenv("ALLOW_SQLITE_PROD_SEED", "0")
        path = Path("data/processed/fighters_list.jsonl")

        with pytest.raises(SystemExit) as exc_info:
            check_sqlite_production_seed_safety("sqlite", path)

        assert exc_info.value.code == 1


class TestDatabaseInitialization:
    """Test that startup enforces PostgreSQL-only configuration."""

    @pytest.mark.asyncio
    @patch("backend.main.get_database_type")
    async def test_lifespan_rejects_non_postgres(self, mock_get_type):
        """Startup fails fast when a non-PostgreSQL backend is detected."""

        mock_get_type.return_value = "sqlite"

        from fastapi import FastAPI

        from backend.main import lifespan

        app = FastAPI()

        with pytest.raises(RuntimeError):
            async with lifespan(app):
                pass

    @pytest.mark.asyncio
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
