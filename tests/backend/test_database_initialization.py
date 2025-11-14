"""Tests for database initialization, preflight checks, and seed safety."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.db.connection import get_database_type, get_database_url


class TestDatabaseType:
    """Test database type detection."""

    def test_get_database_type_requires_database_url(self, monkeypatch) -> None:
        """Missing ``DATABASE_URL`` now surfaces a runtime error."""
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(RuntimeError):
            get_database_type()

    def test_get_database_type_postgresql(self, monkeypatch) -> None:
        """A valid PostgreSQL URL reports the postgresql backend."""
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql+psycopg://user:pass@localhost/db"
        )

        assert get_database_type() == "postgresql"


class TestDatabaseURL:
    """Test database URL construction and sanitization."""

    def test_get_database_url_requires_postgresql(self, monkeypatch) -> None:
        """Missing ``DATABASE_URL`` now raises a configuration error."""
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(RuntimeError):
            get_database_url()

    def test_get_database_url_postgresql(self, monkeypatch) -> None:
        """Test that PostgreSQL ``DATABASE_URL`` is returned unchanged."""
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


class TestDatabaseInitialization:
    """Test that tables are created correctly based on database type."""

    @pytest.mark.asyncio
    @patch("backend.main.get_database_url")
    @patch("backend.main.get_database_type")
    async def test_lifespan_rejects_non_postgresql(
        self,
        mock_get_type: MagicMock,
        mock_get_url: MagicMock,
    ) -> None:
        """Startup should fail fast when a non-PostgreSQL backend is detected."""
        from fastapi import FastAPI

        from backend.main import lifespan

        mock_get_type.return_value = "sqlite"
        mock_get_url.return_value = "sqlite+aiosqlite:///test.db"

        app = FastAPI()

        with pytest.raises(RuntimeError):
            async with lifespan(app):
                pass

    @pytest.mark.asyncio
    @patch("backend.main.get_database_url")
    @patch("backend.warmup.warmup_all", new_callable=AsyncMock)
    @patch("backend.main.get_database_type")
    @patch("backend.main.get_engine")
    async def test_postgresql_warmup_invoked(
        self,
        mock_get_engine: MagicMock,
        mock_get_type: MagicMock,
        mock_warmup: AsyncMock,
        mock_get_url: MagicMock,
    ) -> None:
        """PostgreSQL startup should run the warmup routine with the engine resolver."""
        from fastapi import FastAPI

        from backend.main import lifespan

        mock_get_type.return_value = "postgresql"
        mock_get_url.return_value = "postgresql+psycopg://user:pass@localhost/db"

        app = FastAPI()

        async with lifespan(app):
            pass

        mock_warmup.assert_awaited_once()
        awaited_call = mock_warmup.await_args
        assert awaited_call is not None
        assert awaited_call.kwargs.get("resolve_engine") is mock_get_engine

    @pytest.mark.asyncio
    @patch("backend.scripts.seed_fighters.get_database_type")
    async def test_seed_script_ensure_tables_requires_postgresql(
        self, mock_get_type: MagicMock
    ) -> None:
        """Ensure the seeding helper refuses to operate on non-PostgreSQL engines."""
        from backend.scripts.seed_fighters import ensure_tables

        mock_get_type.return_value = "sqlite"

        with pytest.raises(RuntimeError):
            await ensure_tables()

    @pytest.mark.asyncio
    @patch("backend.scripts.seed_fighters.get_database_type")
    async def test_seed_script_ensure_tables_allows_postgresql(
        self, mock_get_type: MagicMock
    ) -> None:
        """PostgreSQL environments should allow the no-op ensure_tables helper."""
        from backend.scripts.seed_fighters import ensure_tables

        mock_get_type.return_value = "postgresql"

        await ensure_tables()


class TestSeedScriptCli:
    """Test the streamlined PostgreSQL-only fighter seeding CLI."""

    @pytest.mark.asyncio
    @patch("backend.scripts.seed_fighters.validate_environment")
    @patch("backend.scripts.seed_fighters.get_database_type")
    async def test_main_rejects_non_postgresql(
        self,
        mock_get_type: MagicMock,
        mock_validate_environment: MagicMock,
        request: pytest.FixtureRequest,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The CLI should fail fast when the database is not PostgreSQL."""
        from backend.scripts.seed_fighters import main

        del request
        mock_get_type.return_value = "sqlite"
        mock_validate_environment.return_value = None
        monkeypatch.setattr(
            "sys.argv",
            ["seed_fighters", "./data/fixtures/fighters.jsonl"],
            raising=False,
        )

        exit_code = await main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "requires PostgreSQL" in captured.err

    @pytest.mark.asyncio
    @patch("backend.scripts.seed_fighters.validate_environment")
    @patch("backend.scripts.seed_fighters.seed_fighters", new_callable=AsyncMock)
    @patch("backend.scripts.seed_fighters.get_database_type")
    async def test_main_invokes_seeding_for_postgresql(
        self,
        mock_get_type: MagicMock,
        mock_seed: AsyncMock,
        mock_validate_environment: MagicMock,
        request: pytest.FixtureRequest,
        tmp_path: Path,
        tmp_path_factory: pytest.TempPathFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Valid PostgreSQL runs should pass parsed arguments to ``seed_fighters``."""
        from backend.scripts.seed_fighters import main

        del request
        del tmp_path_factory
        data_file = tmp_path / "fighters.jsonl"
        data_file.write_text("{}\n", encoding="utf-8")

        mock_get_type.return_value = "postgresql"
        mock_validate_environment.return_value = None
        mock_seed.return_value = (1, 0)

        monkeypatch.setattr(
            "sys.argv",
            ["seed_fighters", str(data_file), "--limit", "1", "--dry-run"],
            raising=False,
        )

        exit_code = await main()

        assert exit_code == 0
        mock_seed.assert_awaited_once_with(data_file, limit=1, dry_run=True)
