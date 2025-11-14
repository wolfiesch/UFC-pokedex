#!/usr/bin/env python
"""Seed minimal fighter data into a PostgreSQL database from a JSONL file.

This script loads minimal fighter columns required by the /fighters endpoint.
It now targets PostgreSQL exclusively to align with production parity.

Usage:
    python -m backend.scripts.seed_fighters [path_to_jsonl]
    python -m backend.scripts.seed_fighters ./data/fixtures/fighters.jsonl
    python -m backend.scripts.seed_fighters ./data/processed/fighters_list.jsonl --limit 50
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from backend.db.connection import (
    get_engine as _connection_get_engine,
)
from backend.db.connection import (
    get_session,
)
from backend.db.models import Fighter
from backend.main import validate_environment


def get_database_type() -> str:
    """Expose the database type helper for unit tests."""

    from backend.db.connection import get_database_type as _connection_get_database_type

    return _connection_get_database_type()


def get_engine() -> AsyncEngine:
    """Expose the async engine factory for unit tests."""

    return _connection_get_engine()


def parse_date(value: str | None) -> date | None:
    """Parse date string in YYYY-MM-DD format."""
    if not value or value.strip() in ("", "--", "None"):
        return None
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        return None


def require_postgresql_database(db_type: str) -> None:
    """Ensure the target database is PostgreSQL before running the seed routine."""

    if db_type == "postgresql":
        return

    print("=" * 70)
    print("❌  PostgreSQL database required")
    print("=" * 70)
    print()
    print(
        "This seeding workflow expects a PostgreSQL database so that the seeded data matches"
    )
    print("production behaviour and schema constraints.")
    print()
    print("Next steps:")
    print("  • Start PostgreSQL (e.g., `docker compose up -d`).")
    print("  • Apply migrations via Alembic (e.g., `make db-upgrade`).")
    print("  • Re-run this script once the DATABASE_URL points to PostgreSQL.")
    print()
    print(
        "If you intended to load sample data into SQLite, use `make api:seed` instead."
    )
    print()
    sys.exit(1)


async def seed_fighters(
    jsonl_path: Path,
    *,
    limit: int | None = None,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Load fighters from JSONL file into database.

    Args:
        jsonl_path: Path to JSONL file with fighter data
        limit: Maximum number of fighters to load
        dry_run: If True, validate without inserting

    Returns:
        Tuple of (loaded_count, skipped_count)
    """
    if not jsonl_path.exists():
        print(f"❌ File not found: {jsonl_path}", file=sys.stderr)
        return 0, 0

    loaded_count = 0
    skipped_count = 0

    async with get_session() as session:
        with open(jsonl_path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                if limit and loaded_count >= limit:
                    break

                try:
                    # Parse JSON line
                    data = json.loads(line.strip())

                    # Extract fighter_id (required)
                    fighter_id = data.get("fighter_id") or data.get("id")
                    if not fighter_id:
                        print(f"⚠️  Line {line_num}: Missing fighter_id, skipping")
                        skipped_count += 1
                        continue

                    # Extract name (required)
                    name = data.get("name")
                    if not name:
                        print(f"⚠️  Line {line_num}: Missing name, skipping")
                        skipped_count += 1
                        continue

                    if dry_run:
                        print(f"✓ Would load: {name} ({fighter_id})")
                        loaded_count += 1
                        continue

                    # Create Fighter model with minimal columns
                    fighter = Fighter(
                        id=fighter_id,
                        name=name,
                        nickname=data.get("nickname"),
                        division=data.get("division"),
                        record=data.get("record"),
                        height=data.get("height"),
                        weight=data.get("weight"),
                        reach=data.get("reach"),
                        leg_reach=data.get("leg_reach"),
                        stance=data.get("stance"),
                        dob=parse_date(data.get("dob")),
                    )

                    # Upsert (merge) to handle duplicates idempotently
                    await session.merge(fighter)
                    loaded_count += 1

                    # Commit in batches of 100 for performance
                    if loaded_count % 100 == 0:
                        await session.commit()
                        print(f"💾 Committed {loaded_count} fighters...")

                except json.JSONDecodeError as e:
                    print(f"❌ Line {line_num}: Invalid JSON: {e}", file=sys.stderr)
                    skipped_count += 1
                except Exception as e:
                    print(
                        f"❌ Line {line_num}: Error loading fighter: {e}",
                        file=sys.stderr,
                    )
                    if session.in_transaction():
                        await session.rollback()
                    skipped_count += 1

        # Final commit for remaining records
        if not dry_run and session.in_transaction():
            await session.commit()

    return loaded_count, skipped_count


async def main() -> int:
    """CLI entry point."""
    # Mirror the FastAPI startup diagnostics for parity with ``uvicorn`` based
    # launches now that environment validation occurs during lifespan startup.
    validate_environment()

    parser = argparse.ArgumentParser(
        description="Seed minimal fighter data into a PostgreSQL database"
    )
    parser.add_argument(
        "jsonl_path",
        nargs="?",
        type=Path,
        default=Path("./data/fixtures/fighters.jsonl"),
        help="Path to JSONL file (default: ./data/fixtures/fighters.jsonl)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of fighters to load",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate data without inserting into database",
    )

    args = parser.parse_args()

    db_type = get_database_type()
    print(f"🗄️  Database type detected: {db_type.upper()}")
    print(f"📂 Seed source: {args.jsonl_path}")
    if args.limit:
        print(f"🔢 Limit: {args.limit} fighters")
    if args.dry_run:
        print("🔍 Dry run mode (no changes will be made)")
    print(
        "🧭 Reminder: run Alembic migrations (e.g., `make db-upgrade`) before seeding."
    )
    print()

    # Ensure we are targeting PostgreSQL before seeding to maintain parity with production.
    require_postgresql_database(db_type)

    # Run seeding
    loaded, skipped = await seed_fighters(
        args.jsonl_path, limit=args.limit, dry_run=args.dry_run
    )

    # Summary
    print()
    print("=" * 50)
    if args.dry_run:
        print(f"✓ Validated {loaded} fighters")
    else:
        print(f"✅ Loaded {loaded} fighters")
    if skipped > 0:
        print(f"⚠️  Skipped {skipped} records")
    print("=" * 50)

    return 0 if skipped == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
