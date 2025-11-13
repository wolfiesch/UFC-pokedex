"""Unit tests for :mod:`backend.db.connection` URL normalization helpers."""

from __future__ import annotations

import os
from typing import Generator

import pytest

from backend.db.connection import get_database_url


@pytest.fixture(autouse=True)
def cleanup_environment() -> Generator[None, None, None]:
    """Ensure database-related environment variables do not leak between tests."""

    original_database_url = os.environ.get("DATABASE_URL")
    try:
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]
        yield
    finally:
        if original_database_url is not None:
            os.environ["DATABASE_URL"] = original_database_url
        else:
            os.environ.pop("DATABASE_URL", None)


def test_get_database_url_normalizes_legacy_postgres_scheme() -> None:
    """``postgres://`` URLs are upgraded to the async psycopg dialect automatically."""

    os.environ["DATABASE_URL"] = "postgres://user:pass@localhost:5432/dbname"

    normalized_url = get_database_url()

    assert normalized_url == "postgresql+psycopg://user:pass@localhost:5432/dbname"


def test_get_database_url_normalizes_postgresql_scheme() -> None:
    """``postgresql://`` URLs are upgraded to the async psycopg dialect automatically."""

    os.environ["DATABASE_URL"] = "postgresql://user:pass@host/db"

    normalized_url = get_database_url()

    assert normalized_url == "postgresql+psycopg://user:pass@host/db"


def test_get_database_url_accepts_normalized_url() -> None:
    """Already-normalized URLs are returned unchanged."""

    expected_url = "postgresql+psycopg://user:pass@db.example.com:6543/ufc"
    os.environ["DATABASE_URL"] = expected_url

    normalized_url = get_database_url()

    assert normalized_url == expected_url
