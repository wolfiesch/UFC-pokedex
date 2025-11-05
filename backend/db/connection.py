from __future__ import annotations

import os
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


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

    # Validate PostgreSQL URL format
    if not url.startswith("postgresql+psycopg"):
        raise RuntimeError("Expected asynchronous psycopg URL, got %s" % url)
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
        return create_async_engine(
            url,
            future=True,
            echo=False,
            pool_size=10,  # Maintain 10 warm connections
            max_overflow=20,  # Allow up to 30 total connections
            pool_pre_ping=True,  # Validate connections before use
            pool_recycle=1800,  # Recycle connections every 30 min
        )

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


# Global engine instance for FastAPI dependency injection
_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """Get or create the global engine instance."""
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


async def get_db() -> AsyncSession:
    """FastAPI dependency that provides a database session."""
    engine = get_engine()
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
