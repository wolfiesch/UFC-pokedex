"""Query performance monitoring for the UFC Pokedex application.

This module provides tools to monitor slow database queries and identify performance bottlenecks.
"""

import logging
import time
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

logger = logging.getLogger(__name__)


def setup_query_monitoring(
    engine: Engine,
    slow_query_threshold: float = 0.1,
    log_pool_stats: bool = True,
) -> None:
    """Set up database query performance monitoring.

    This will log warnings for queries that exceed the slow query threshold,
    helping identify performance bottlenecks.

    Args:
        engine: SQLAlchemy engine to monitor
        slow_query_threshold: Log queries slower than this many seconds (default: 0.1s = 100ms)
        log_pool_stats: Whether to log connection pool statistics (default: True)
    """
    if not hasattr(engine, "sync_engine"):
        logger.warning("Engine does not have sync_engine attribute, skipping query monitoring")
        return

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def receive_before_cursor_execute(
        conn: Any,  # SQLAlchemy Connection - using Any due to incomplete typing in library
        cursor: Any,  # DBAPI cursor - type varies by database driver
        statement: str,
        parameters: Any,  # Query parameters - type varies by query
        context: Any,  # ExecutionContext - using Any due to incomplete typing in library
        executemany: bool,
    ) -> None:
        """Record query start time."""
        conn.info.setdefault("query_start_time", []).append(time.time())

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def receive_after_cursor_execute(
        conn: Any,  # SQLAlchemy Connection - using Any due to incomplete typing in library
        cursor: Any,  # DBAPI cursor - type varies by database driver
        statement: str,
        parameters: Any,  # Query parameters - type varies by query
        context: Any,  # ExecutionContext - using Any due to incomplete typing in library
        executemany: bool,
    ) -> None:
        """Log slow queries after execution."""
        total = time.time() - conn.info["query_start_time"].pop()

        if total > slow_query_threshold:
            # Truncate statement for logging (first 500 chars)
            truncated_statement = statement[:500]
            if len(statement) > 500:
                truncated_statement += "..."

            logger.warning(
                f"Slow query detected ({total:.3f}s): {truncated_statement}",
                extra={
                    "duration_seconds": total,
                    "query": statement,
                    "parameters": parameters,
                    "threshold_seconds": slow_query_threshold,
                },
            )

    if log_pool_stats:
        # Log connection pool statistics periodically
        @event.listens_for(Pool, "connect")
        def receive_connect(
            dbapi_conn: Any,  # DBAPI connection - type varies by database driver
            connection_record: Any,  # PoolProxiedConnection - using Any due to incomplete typing
        ) -> None:
            """Log when new connections are created."""
            logger.debug("New database connection created")

        @event.listens_for(Pool, "checkout")
        def receive_checkout(
            dbapi_conn: Any,  # DBAPI connection - type varies by database driver
            connection_record: Any,  # ConnectionPoolEntry - using Any due to incomplete typing
            connection_proxy: Any,  # PoolProxiedConnection - using Any due to incomplete typing
        ) -> None:
            """Log connection pool checkout."""
            pool = connection_proxy._pool
            logger.debug(
                f"Connection checked out from pool. "
                f"Pool size: {pool.size()}, "
                f"Checked out: {pool.checkedout()}, "
                f"Overflow: {pool.overflow()}"
            )

    logger.info(
        f"Query performance monitoring enabled "
        f"(slow query threshold: {slow_query_threshold}s, "
        f"pool stats logging: {log_pool_stats})"
    )


def log_pool_status(engine: Engine) -> None:
    """Log current connection pool status for debugging.

    This can be called manually to check pool health.
    """
    if not hasattr(engine, "pool"):
        logger.warning("Engine does not have pool attribute")
        return

    pool = engine.pool
    logger.info(
        f"Connection Pool Status: "
        f"size={pool.size()}, "
        f"checked_out={pool.checkedout()}, "
        f"overflow={pool.overflow()}, "
        f"pool_size={pool._pool.qsize() if hasattr(pool, '_pool') else 'N/A'}"
    )
