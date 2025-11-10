"""Backend warmup module to eliminate cold start delays.

This module provides warmup functions for database, Redis, and repository queries
to ensure all connections and caches are hot before serving the first request.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.db.connection import begin_engine_transaction

logger = logging.getLogger(__name__)


async def warmup_database(
    resolve_db_type: Callable[[], str] | None = None,
    resolve_engine: Callable[[], AsyncEngine] | None = None,
) -> None:
    """Warm up database connection pool.

    Executes a simple query to initialize the connection pool and ORM machinery.
    Gracefully degrades if warmup fails.
    """
    try:
        if resolve_db_type is None:
            from backend.db.connection import get_database_type as resolve_db_type

        if resolve_engine is None:
            from backend.db.connection import get_engine as resolve_engine

        start = time.time()
        db_type = resolve_db_type()
        logger.debug("Database warmup target detected as %s", db_type)
        if db_type != "sqlite":
            logger.debug(
                "Skipping database warmup for non-SQLite backend '%s'", db_type
            )
            return

        engine = resolve_engine()

        async with begin_engine_transaction(engine) as conn:
            # Simple ping query to warm up connection
            await conn.execute(text("SELECT 1"))

        elapsed = (time.time() - start) * 1000
        logger.info(f"✓ Database connection warmed up ({elapsed:.0f}ms)")
    except Exception as e:
        logger.warning(f"Database warmup failed: {e}")


async def warmup_redis() -> None:
    """Warm up Redis connection.

    Establishes connection and tests with PING command.
    Gracefully degrades if Redis is unavailable.
    """
    from backend.cache import get_redis

    try:
        start = time.time()
        redis = await get_redis()

        if redis is None:
            logger.info("⚠ Redis warmup skipped (connection unavailable)")
            return

        # Test connection with PING
        await redis.ping()

        elapsed = (time.time() - start) * 1000
        logger.info(f"✓ Redis connection warmed up ({elapsed:.0f}ms)")
    except Exception as e:
        logger.warning(f"Redis warmup failed: {e}")


async def warmup_repository_queries(
    resolve_db_type: Callable[[], str] | None = None,
) -> None:
    """Warm up common repository queries.

    Executes lightweight queries to initialize ORM mappers and relationship loaders.
    Gracefully degrades if warmup fails.
    """
    from backend.db.connection import get_db
    from backend.db.models import Fighter
    from backend.db.repositories import PostgreSQLFighterRepository

    try:
        start = time.time()

        if resolve_db_type is None:
            from backend.db.connection import get_database_type as resolve_db_type

        db_type = resolve_db_type()

        if db_type != "sqlite":
            async for session in get_db():
                await session.execute(select(Fighter.id).limit(1))
                break

            elapsed = (time.time() - start) * 1000
            logger.info(
                "✓ Repository warmup (lightweight) executed (%s, %.0fms)",
                db_type,
                elapsed,
            )
            return

        async for session in get_db():
            repo = PostgreSQLFighterRepository(session)

            # Warmup query: Fetch 1 fighter with relationships
            # This initializes ORM mappers and relationship loaders
            await repo.list_fighters(limit=1, offset=0)
            break  # Only need one iteration

        elapsed = (time.time() - start) * 1000
        logger.info(f"✓ Repository queries warmed up ({elapsed:.0f}ms)")
    except Exception as e:
        logger.warning(f"Repository warmup failed: {e}")


async def warmup_all(
    resolve_db_type: Callable[[], str] | None = None,
    resolve_engine: Callable[[], AsyncEngine] | None = None,
) -> None:
    """Warm up all backend connections and caches.

    Executes all warmup functions in sequence and logs total warmup time.
    """
    logger.info("=" * 60)
    logger.info("Warming up backend connections...")
    logger.info("=" * 60)

    start = time.time()

    await warmup_database(
        resolve_db_type=resolve_db_type,
        resolve_engine=resolve_engine,
    )
    await warmup_redis()
    await warmup_repository_queries(resolve_db_type=resolve_db_type)

    total_elapsed = (time.time() - start) * 1000
    logger.info("=" * 60)
    logger.info(f"✓ Backend warmup complete ({total_elapsed:.0f}ms)")
    logger.info("=" * 60)
