"""Tests for database initialization, preflight checks, and seed safety."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.db.connection import get_database_type, get_database_url
from backend.scripts.seed_fighters import require_postgresql_database


class TestDatabaseType:
    """Test database type detection."""

    def test_get_database_type_postgresql(self, monkeypatch):
        """Valid PostgreSQL URLs should return the expected identifier."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+psycopg://user:pass@localhost/db",
        )
        assert get_database_type() == "postgresql"

    def test_get_database_type_missing_url_raises(self, monkeypatch):
        """Missing DATABASE_URL should raise a RuntimeError."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(RuntimeError):
            get_database_type()


class TestDatabaseURL:
    """Test database URL construction and sanitization."""

    def test_get_database_url_missing_env_raises(self, monkeypatch):
        """Missing DATABASE_URL should raise a RuntimeError."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(RuntimeError):
            get_database_url()

    def test_get_database_url_normalizes_postgres_scheme(self, monkeypatch):
        """Legacy postgres URLs should normalize to the async driver scheme."""
        monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/db")
        url = get_database_url()
        assert url == "postgresql+psycopg://user:pass@localhost:5432/db"

    def test_get_database_url_accepts_psycopg_scheme(self, monkeypatch):
        """Modern psycopg URLs should pass through unchanged."""
        pg_url = "postgresql+psycopg://user:pass@localhost/db"
        monkeypatch.setenv("DATABASE_URL", pg_url)
        assert get_database_url() == pg_url


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


class TestSeedDatabaseValidation:
    """Test the PostgreSQL-only gating logic for the fighter seed script."""

    def test_allows_postgresql(self, capsys):
        """PostgreSQL should not raise and should be silent."""
        require_postgresql_database("postgresql")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_blocks_non_postgresql(self, capsys):
        """Non-PostgreSQL databases should halt execution with guidance."""
        with pytest.raises(SystemExit) as exc_info:
            require_postgresql_database("sqlite")

        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "PostgreSQL database required" in captured.out
        assert "Alembic" in captured.out


class TestDatabaseInitialization:
    """Test that tables are created correctly based on database type."""

    @pytest.mark.asyncio
    @patch("backend.main.get_database_url")
    @patch("backend.main.get_database_type")
    async def test_non_postgresql_database_type_raises(
        self, mock_get_type, mock_get_url
    ) -> None:
        """A non-PostgreSQL database type should trigger a RuntimeError."""
        mock_get_type.return_value = "sqlite"
        mock_get_url.return_value = "postgresql+psycopg://user:pass@localhost/db"

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
