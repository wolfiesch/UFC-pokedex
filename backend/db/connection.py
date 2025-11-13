from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.settings import AppSettings, settings

logger = logging.getLogger(__name__)


def get_database_url(active_settings: AppSettings | None = None) -> str:
    """Return the normalized database URL derived from shared settings."""

    settings_obj = active_settings or settings
    return settings_obj.resolved_database_url


def get_database_type(active_settings: AppSettings | None = None) -> str:
    """Return the database dialect reported by the settings instance."""

    settings_obj = active_settings or settings
    return settings_obj.database_type


def create_engine(active_settings: AppSettings | None = None) -> AsyncEngine:
    """Create an async engine using configuration captured in ``AppSettings``.

    For PostgreSQL:
    - pool_size=10: Maintain 10 warm connections
    - max_overflow=20: Allow up to 30 total connections
    - pool_pre_ping=True: Validate connections before use
    - pool_recycle=1800: Recycle connections every 30 minutes

    For SQLite:
    - No pooling parameters (not supported)
    """

    settings_obj = active_settings or settings
    db_type = settings_obj.database_type
    url = settings_obj.resolved_database_url

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
            setup_query_monitoring(
                engine,
                slow_query_threshold=settings_obj.slow_query_threshold,
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
        # Note: Don't rollback in finally - if commit() was called successfully,
        # rolling back would undo the committed work
