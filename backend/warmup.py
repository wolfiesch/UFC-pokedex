"""Backend warmup module to eliminate cold start delays.

This module provides warmup functions for database, Redis, and repository queries
to ensure all connections and caches are hot before serving the first request.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.db.connection import begin_engine_transaction

logger = logging.getLogger(__name__)


async def warmup_database(
    resolve_db_type: Callable[[], str] | None = None,
    resolve_engine: Callable[[], AsyncEngine] | None = None,
) -> None:
    """Warm up the PostgreSQL connection pool by executing a ping query.

    The warmup now always opens a pooled transaction and issues ``SELECT 1`` so the
    PostgreSQL driver establishes a connection ahead of the first request.  When a
    different database type is detected we log a warning but still perform the ping
    so misconfigurations surface quickly during startup.
    """
    try:
        if resolve_db_type is None:
            from backend.db.connection import get_database_type as resolve_db_type

        if resolve_engine is None:
            from backend.db.connection import get_engine as resolve_engine

        start = time.time()
        db_type = resolve_db_type()
        logger.debug("Database warmup target detected as %s", db_type)

        if db_type != "postgresql":
            logger.warning(
                "Database warmup expected PostgreSQL but detected '%s'; continuing",
                db_type,
            )

        engine = resolve_engine()

        # For pooled databases (e.g., PostgreSQL) run a lightweight ping so the pool
        # establishes an initial connection before serving traffic.
        async with begin_engine_transaction(engine) as conn:
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
    """Warm up PostgreSQL repository queries.

    The warmup always instantiates the PostgreSQL fighter repository so its mappers
    and loader strategies are prepared before the application begins handling
    traffic.  Non-PostgreSQL configurations trigger a warning but still run the
    warmup query to avoid silently skipping initialization work.
    """
    from backend.db.connection import get_db
    from backend.db.repositories import PostgreSQLFighterRepository

    try:
        start = time.time()

        if resolve_db_type is None:
            from backend.db.connection import get_database_type as resolve_db_type

        db_type = resolve_db_type()

        if db_type != "postgresql":
            logger.warning(
                "Repository warmup expected PostgreSQL but detected '%s'; continuing",
                db_type,
            )

        async for session in get_db():
            repo = PostgreSQLFighterRepository(session)

            # Warmup query: Fetch 1 fighter with relationships to prime the ORM
            # loader strategies that are used heavily in production workloads.
            await repo.list_fighters(limit=1, offset=0)
            break  # Only need one iteration

        elapsed = (time.time() - start) * 1000
        logger.info(
            "✓ Repository warmup executed (%.0fms)",
            elapsed,
        )
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
