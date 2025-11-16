"""Utilities and fixtures for working with ephemeral PostgreSQL schemas in tests."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import pytest
from pytest import MonkeyPatch
from sqlalchemy import MetaData
from sqlalchemy import schema as sa_schema
from sqlalchemy.engine import URL, Engine
from sqlalchemy.engine import create_engine as create_sync_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.exc import OperationalError


@dataclass(frozen=True)
class TemporaryPostgresSchema:
    """Descriptor for a throwaway PostgreSQL schema dedicated to a single test."""

    name: str
    url: URL

    @property
    def sqlalchemy_url(self) -> str:
        """Return the SQLAlchemy connection URL with ``search_path`` preset."""

        return self.url.render_as_string(hide_password=False)

    def create_async_engine(self, **kwargs: Any) -> AsyncEngine:
        """Create an :class:`AsyncEngine` scoped to the temporary schema."""

        return create_async_engine(self.sqlalchemy_url, **kwargs)

    def create_sync_engine(self, **kwargs: Any) -> Engine:
        """Create a synchronous engine scoped to the temporary schema."""

        return create_sync_engine(self.sqlalchemy_url, future=True, **kwargs)

    @asynccontextmanager
    async def session_scope(self, metadata: MetaData) -> AsyncIterator[AsyncSession]:
        """Yield an async session bound to the schema and ensure cleanup."""

        engine = self.create_async_engine()
        async with engine.begin() as connection:
            await connection.run_sync(metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.rollback()

        await engine.dispose()

    def install_as_default(self, monkeypatch: MonkeyPatch) -> None:
        """Point ``DATABASE_URL`` at the schema so application code uses it."""

        monkeypatch.delenv("USE_SQLITE", raising=False)
        monkeypatch.setenv("DATABASE_URL", self.sqlalchemy_url)


def _base_url() -> URL:
    """Resolve the base PostgreSQL URL used to mint per-test schemas."""

    raw_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if raw_url:
        url = make_url(raw_url)
    else:
        url = URL.create(
            "postgresql+psycopg",
            username=os.getenv("TEST_DB_USER", "test"),
            password=os.getenv("TEST_DB_PASSWORD", "test"),
            host=os.getenv("TEST_DB_HOST", "127.0.0.1"),
            port=int(os.getenv("TEST_DB_PORT", "5432")),
            database=os.getenv("TEST_DB_NAME", "postgres"),
        )

    if url.get_backend_name() != "postgresql":
        raise RuntimeError("TemporaryPostgresSchema requires a PostgreSQL URL")

    if url.get_driver_name() != "psycopg":
        url = url.set(drivername="postgresql+psycopg")

    return url


def _url_with_schema(schema_name: str) -> URL:
    """Embed ``schema_name`` into the base URL via ``search_path`` options."""

    base = _base_url()
    query: dict[str, Any] = dict(base.query)
    search_path_clause = f"-csearch_path={schema_name}"
    if "options" in query:
        query["options"] = f"{query['options']} {search_path_clause}".strip()
    else:
        query["options"] = search_path_clause
    return base.set(query=query)


@pytest.fixture()
def postgres_schema() -> Iterator[TemporaryPostgresSchema]:
    """Yield a PostgreSQL schema that is dropped after the test completes."""

    schema_name = f"test_{uuid.uuid4().hex}"
    admin_engine = create_sync_engine(_base_url(), future=True)

    try:
        with admin_engine.begin() as connection:
            connection.execute(sa_schema.CreateSchema(schema_name))
    except OperationalError as exc:
        # Creating a schema fails immediately when PostgreSQL is unavailable.
        # Skipping the test suite rather than crashing keeps local development
        # environments without a running database usable while still surfacing
        # the exact error to anyone investigating the skip reason.
        admin_engine.dispose()
        pytest.skip(
            (
                "PostgreSQL is required for this test but the database is unreachable: "
                f"{exc}"
            )
        )

    schema = TemporaryPostgresSchema(
        name=schema_name, url=_url_with_schema(schema_name)
    )

    try:
        yield schema
    finally:
        with admin_engine.begin() as connection:
            connection.execute(sa_schema.DropSchema(schema_name, cascade=True))
        admin_engine.dispose()
