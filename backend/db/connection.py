from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from environment or fallback to SQLite.

    Returns:
        Database URL string. Falls back to SQLite if DATABASE_URL is not set
        or if USE_SQLITE=1 is set in environment.
    """
    # Force SQLite mode if USE_SQLITE=1 is set
    use_sqlite = os.getenv("USE_SQLITE", "").strip() == "1"

    if use_sqlite:
        return "sqlite+aiosqlite:///./data/app.db"

    url = os.getenv("DATABASE_URL")
    if not url:
        # Fallback to SQLite when DATABASE_URL is not set
        return "sqlite+aiosqlite:///./data/app.db"

    # Auto-convert standard PostgreSQL URLs to async psycopg format. The
    # ``postgres://`` URI scheme is still common in legacy Heroku setups, so we
    # normalize it alongside ``postgresql://`` for compatibility.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif not url.startswith("postgresql+psycopg://"):
        raise RuntimeError(f"Expected PostgreSQL URL, got {url}")

    return url


def get_database_type() -> str:
    """Detect database type from URL.

    Returns:
        "sqlite" or "postgresql"
    """
    url = get_database_url()
    if url.startswith("sqlite"):
        return "sqlite"
    return "postgresql"


def create_engine() -> AsyncEngine:
    """Create async database engine with optimized connection pooling.

    For PostgreSQL:
    - pool_size=10: Maintain 10 warm connections
    - max_overflow=20: Allow up to 30 total connections
    - pool_pre_ping=True: Validate connections before use
    - pool_recycle=1800: Recycle connections every 30 minutes

    For SQLite:
    - No pooling parameters (not supported)
    """
    db_type = get_database_type()
    url = get_database_url()

    if db_type == "postgresql":
        # PostgreSQL: Optimize connection pooling
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

        # Enable query performance monitoring for PostgreSQL
        try:
            from backend.monitoring import setup_query_monitoring

            # Get slow query threshold from environment (default: 100ms)
            slow_query_threshold = float(os.getenv("SLOW_QUERY_THRESHOLD", "0.1"))
            setup_query_monitoring(
                engine,
                slow_query_threshold=slow_query_threshold,
                log_pool_stats=False,  # Disable verbose pool logging by default
            )
        except Exception as e:
            logger.warning(f"Failed to enable query monitoring: {e}")

        return engine

    # SQLite: No pooling needed
    return create_async_engine(url, future=True, echo=False)


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
        finally:
            # Ensure no dangling transactions remain open
            if session.in_transaction():
                await session.rollback()
