"""Backend warmup module to eliminate cold start delays.

This module provides warmup functions for database, Redis, and repository queries
to ensure all connections and caches are hot before serving the first request.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy import text

logger = logging.getLogger(__name__)


async def warmup_database() -> None:
    """Warm up database connection pool.

    Executes a simple query to initialize the connection pool and ORM machinery.
    Gracefully degrades if warmup fails.
    """
    from backend.db.connection import get_database_type, get_engine

    engine = get_engine()
    db_type = get_database_type()

    try:
        start = time.time()
        async with engine.begin() as conn:
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


async def warmup_repository_queries() -> None:
    """Warm up common repository queries.

    Executes lightweight queries to initialize ORM mappers and relationship loaders.
    Gracefully degrades if warmup fails.
    """
    from backend.db.connection import get_db
    from backend.db.repositories import PostgreSQLFighterRepository

    try:
        start = time.time()

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


async def warmup_all() -> None:
    """Warm up all backend connections and caches.

    Executes all warmup functions in sequence and logs total warmup time.
    """
    logger.info("=" * 60)
    logger.info("Warming up backend connections...")
    logger.info("=" * 60)

    start = time.time()

    await warmup_database()
    await warmup_redis()
    await warmup_repository_queries()

    total_elapsed = (time.time() - start) * 1000
    logger.info("=" * 60)
    logger.info(f"✓ Backend warmup complete ({total_elapsed:.0f}ms)")
    logger.info("=" * 60)
