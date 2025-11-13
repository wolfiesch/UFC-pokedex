from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from urllib.parse import urlsplit

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


def _validate_postgres_url(database_url: str) -> str:
    """Normalize and validate a PostgreSQL connection string.

    The helper keeps the validation logic concentrated in one place so callers
    can rely on a single, well-documented error message surface.  It upgrades
    legacy DSNs—such as ``postgres://``—to SQLAlchemy's async driver syntax and
    performs lightweight structural checks using :func:`urllib.parse.urlsplit`.
    """

    normalized_url = database_url.strip()
    if not normalized_url:
        raise RuntimeError(
            "DATABASE_URL is set but empty. Provide a valid PostgreSQL connection string."
        )

    if normalized_url.startswith("postgres://"):
        normalized_url = normalized_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif normalized_url.startswith("postgresql://"):
        normalized_url = normalized_url.replace("postgresql://", "postgresql+psycopg://", 1)

    if not normalized_url.startswith("postgresql+psycopg://"):
        raise RuntimeError(
            "DATABASE_URL must use the PostgreSQL scheme. "
            "Expected a URL beginning with 'postgresql://', 'postgres://', or 'postgresql+psycopg://'."
        )

    parts = urlsplit(normalized_url)
    if not parts.hostname or not parts.path:
        raise RuntimeError(
            "DATABASE_URL appears malformed. Verify the host and database name are present."
        )

    return normalized_url


def get_database_url() -> str:
    """Return the PostgreSQL database URL required by the application.

    Accessing the value centralizes configuration validation and ensures every
    code path observes the same high-quality error message when ``DATABASE_URL``
    is missing or malformed.
    """

    database_url = os.getenv("DATABASE_URL")
    if database_url is None:
        raise RuntimeError(
            "DATABASE_URL is not set. Configure it with a PostgreSQL connection string before starting the API."
        )

    return _validate_postgres_url(database_url)


def get_database_type() -> str:
    """Return the active database backend identifier.

    Raising a ``RuntimeError`` for anything other than PostgreSQL guarantees
    that downstream callers—such as FastAPI's lifespan hooks—fail immediately
    rather than quietly defaulting to an unsupported engine.
    """

    url = get_database_url()
    if not url.startswith("postgresql+psycopg://"):
        raise RuntimeError("Only PostgreSQL connections are supported by the API.")
    return "postgresql"


def create_engine() -> AsyncEngine:
    """Create the async SQLAlchemy engine for PostgreSQL.

    The pooling parameters mirror the previous implementation so deployment
    characteristics remain unchanged while the function now enforces a strict
    PostgreSQL-only contract.
    """

    url = get_database_url()
    if not url.startswith("postgresql+psycopg://"):
        raise RuntimeError("create_engine only supports PostgreSQL URLs.")

    engine = create_async_engine(
        url,
        future=True,
        echo=False,
        pool_size=10,  # Maintain 10 warm connections
        max_overflow=20,  # Allow up to 30 total connections
        pool_pre_ping=True,  # Validate connections before use
        pool_recycle=1800,  # Recycle connections every 30 min
        pool_timeout=30,  # Timeout for getting connection from pool
    )

    try:
        from backend.monitoring import setup_query_monitoring

        slow_query_threshold = float(os.getenv("SLOW_QUERY_THRESHOLD", "0.1"))
        setup_query_monitoring(
            engine,
            slow_query_threshold=slow_query_threshold,
            log_pool_stats=False,
        )
    except Exception as exc:  # pragma: no cover - monitoring is optional at runtime
        logger.warning(f"Failed to enable query monitoring: {exc}")

    return engine


def create_session_factory(engine: AsyncEngine) -> sessionmaker[AsyncSession]:
    return sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def get_session(engine: AsyncEngine | None = None):
    engine = engine or create_engine()
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        yield session


@asynccontextmanager
async def begin_engine_transaction(engine: AsyncEngine) -> AsyncIterator[Any]:
    """Yield a connection from ``engine.begin()`` with mock-friendly support."""

    begin_result = engine.begin()
    if asyncio.iscoroutine(begin_result):
        begin_context = await begin_result
    else:
        begin_context = begin_result

    async with begin_context as connection:
        yield connection


# Global engine/session instances for FastAPI dependency injection
_engine: AsyncEngine | None = None
_session_factory: sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the global engine instance."""
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


def get_session_factory() -> sessionmaker[AsyncSession]:
    """Lazily create a session factory bound to the shared engine."""
    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory(get_engine())
    return _session_factory


async def get_db() -> AsyncSession:
    """
    Dependency to provide database session.

    Yields async session and ensures proper cleanup even on errors.
    """
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency that mirrors ``get_db`` but keeps the legacy name.

    Exists for backwards compatibility with routers/scripts that still import
    ``get_async_session``. Automatically commits on success and rolls back on
    error before closing the session.
    """
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_async_session_context() -> AsyncIterator[AsyncSession]:
    """
    Async context manager for scripts/CLI tasks that need manual session control.
    """
    async with get_session_factory()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        # Note: Don't rollback in finally - if commit() was called successfully,
        # rolling back would undo the committed work
