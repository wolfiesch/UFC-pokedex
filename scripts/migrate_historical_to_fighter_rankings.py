"""
Migrate Historical Rankings to Fighter Rankings Table

This script migrates data from the historical_rankings table
(created by import_fightmatrix_historical.py) into the fighter_rankings
table that the API actually queries.

The transformation includes:
- Matching fighter names to fighter IDs
- Mapping division codes/names to standard division names
- Setting source='fightmatrix' for all historical data
- Converting column names (issue_date -> rank_date)

Usage:
    python scripts/migrate_historical_to_fighter_rankings.py
    python scripts/migrate_historical_to_fighter_rankings.py --dry-run
    python scripts/migrate_historical_to_fighter_rankings.py --limit 100

PostgreSQL is required; the script intentionally aborts when SQLite is configured.
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import TypedDict
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, select
from sqlalchemy.engine import Engine, make_url

# Import database connection and models
from backend.db.connection import get_database_url, get_session
from backend.db.models import Fighter

# Import name matcher
from scraper.utils.name_matcher import FighterNameMatcher


# Division name standardization mapping
DIVISION_MAPPING = {
    "Heavyweight": "Heavyweight",
    "LightHeavyweight": "Light Heavyweight",
    "Middleweight": "Middleweight",
    "Welterweight": "Welterweight",
    "Lightweight": "Lightweight",
    "Featherweight": "Featherweight",
    "Bantamweight": "Bantamweight",
    "Flyweight": "Flyweight",
}


def standardize_division_name(division_name: str) -> str:
    """Convert Fight Matrix division names to standard UFC names.

    Args:
        division_name: Division name from Fight Matrix (e.g., 'LightHeavyweight')

    Returns:
        Standardized division name (e.g., 'Light Heavyweight')
    """
    return DIVISION_MAPPING.get(division_name, division_name)


async def load_fighters_for_matching():
    """Load all fighters from database for name matching.

    Returns:
        List of dicts with keys: id, name, nickname, record, division
    """
    async with get_session() as session:
        result = await session.execute(
            select(
                Fighter.id,
                Fighter.name,
                Fighter.nickname,
                Fighter.record,
                Fighter.division,
            )
        )
        rows = result.all()

        fighters_db = []
        for row in rows:
            fighters_db.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "nickname": row.nickname,
                    "record": row.record,
                    "division": row.division,
                }
            )

        return fighters_db


class MigrationStats(TypedDict):
    """Typed structure summarising migration outcomes for logging."""

    total_historical: int
    matched_fighters: int
    unmatched_fighters: int
    inserted: int
    duplicates_skipped: int
    errors: int


async def migrate_historical_rankings_async(
    engine: Engine,
    dry_run: bool = False,
    limit: int | None = None,
) -> MigrationStats:
    """
    Migrate historical rankings to fighter_rankings table.

    Args:
        engine: SQLAlchemy engine
        dry_run: If True, don't actually insert data
        limit: Optional limit on number of records to migrate

    Returns:
        MigrationStats: Dictionary with migration statistics
    """
    stats: MigrationStats = {
        "total_historical": 0,
        "matched_fighters": 0,
        "unmatched_fighters": 0,
        "inserted": 0,
        "duplicates_skipped": 0,
        "errors": 0,
    }

    # Load fighters for name matching
    print("📋 Loading fighters from database for name matching...")
    fighters_db = await load_fighters_for_matching()
    print(f"   Loaded {len(fighters_db):,} fighters")
    print()

    # Initialize name matcher with enhanced nickname support
    matcher = FighterNameMatcher(fighters_db)
    print("✓ Name matcher initialized with nickname support")
    print()

    with engine.connect() as conn:
        # Count total historical rankings
        count_query = text("SELECT COUNT(*) FROM historical_rankings")
        result = conn.execute(count_query)
        stats["total_historical"] = result.scalar()

        print(f"📊 Total historical rankings: {stats['total_historical']:,}")
        print()

        # Fetch historical rankings (WITHOUT joining to fighters table)
        query = text(
            """
            SELECT
                hr.fighter_name,
                hr.division_code,
                hr.division_name,
                hr.rank,
                hr.issue_date
            FROM historical_rankings hr
            ORDER BY hr.issue_date, hr.division_code, hr.rank
            {limit_clause}
        """.format(
                limit_clause=f"LIMIT {limit}" if limit else ""
            )
        )

        result = conn.execute(query)
        rows = result.fetchall()

        print(
            f"📦 Processing {len(rows):,} ranking records with fuzzy name matching..."
        )
        print()

        # Process each ranking
        for i, row in enumerate(rows, 1):
            fighter_name = row[0]
            division_name = row[2]
            rank = row[3]
            issue_date = row[4]

            # Use enhanced name matcher (with nickname support and fuzzy matching)
            standard_division = standardize_division_name(division_name)
            fighter_id, confidence, reason = matcher.match_fighter(
                fighter_name,
                division=standard_division,
                min_confidence=75.0,  # Slightly lower threshold for historical data
            )

            # Track matched vs unmatched
            if fighter_id:
                stats["matched_fighters"] += 1
            else:
                stats["unmatched_fighters"] += 1
                # Skip fighters we can't match
                continue

            if dry_run:
                if i <= 5:  # Show first 5 for dry run
                    print(
                        f"   [DRY RUN] Would insert: {fighter_name} | {standard_division} | Rank {rank} | {issue_date}"
                    )
                continue

            # Check if this ranking already exists
            check_query = text(
                """
                SELECT COUNT(*)
                FROM fighter_rankings
                WHERE fighter_id = :fighter_id
                  AND division = :division
                  AND rank_date = :rank_date
                  AND source = 'fightmatrix'
            """
            )

            exists = conn.execute(
                check_query,
                {
                    "fighter_id": fighter_id,
                    "division": standard_division,
                    "rank_date": issue_date,
                },
            ).scalar()

            if exists > 0:
                stats["duplicates_skipped"] += 1
                continue

            # Insert into fighter_rankings
            try:
                insert_query = text(
                    """
                    INSERT INTO fighter_rankings (
                        id, fighter_id, division, rank,
                        previous_rank, rank_date, source,
                        is_interim, created_at
                    ) VALUES (
                        :id, :fighter_id, :division, :rank,
                        NULL, :rank_date, 'fightmatrix',
                        :is_interim, CURRENT_TIMESTAMP
                    )
                """
                )

                conn.execute(
                    insert_query,
                    {
                        "id": str(uuid4()),
                        "fighter_id": fighter_id,
                        "division": standard_division,
                        "rank": rank,
                        "rank_date": issue_date,
                        "is_interim": False,  # Default to false, can be inferred later
                    },
                )

                stats["inserted"] += 1

                # Progress indicator
                if stats["inserted"] % 1000 == 0:
                    print(f"   ✓ Inserted {stats['inserted']:,} rankings...")

            except Exception as e:
                print(f"   ⚠️  Error inserting {fighter_name}: {e}")
                stats["errors"] += 1

        if not dry_run:
            conn.commit()

    return stats


def resolve_postgres_url(raw_url: str) -> str:
    """
    Validate and normalize the DATABASE_URL for synchronous PostgreSQL access.

    Args:
        raw_url: The raw DATABASE_URL string to validate and normalize.

    Returns:
        str: Normalized PostgreSQL URL with psycopg driver.

    Raises:
        SystemExit: If the URL does not target PostgreSQL.
    """
    url = make_url(raw_url)
    if url.get_backend_name() != "postgresql":
        raise SystemExit(
            "Historical ranking migrations require PostgreSQL; "
            f"detected backend '{url.get_backend_name()}'"
        )

    return str(url.set(drivername="postgresql+psycopg"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate Fight Matrix historical rankings into PostgreSQL"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually inserting data",
    )
    parser.add_argument(
        "--limit", type=int, help="Limit number of records to process (for testing)"
    )

    args = parser.parse_args()

    print("🚀 Historical Rankings Migration")
    print()

    if args.dry_run:
        print("⚠️  DRY RUN MODE - No data will be inserted")
        print()

    # Resolve PostgreSQL URL without supporting legacy SQLite fallbacks.
    database_url = resolve_postgres_url(get_database_url())

    print(
        f"📊 Database: {database_url.split('@')[-1] if '@' in database_url else database_url.split(':///')[-1]}"
    )
    print("🛡️  PostgreSQL URL validated")
    print()

    engine = create_engine(database_url)

    # Run migration (async to use name matcher)
    start_time = datetime.now()
    stats = asyncio.run(
        migrate_historical_rankings_async(engine, args.dry_run, args.limit)
    )
    duration = (datetime.now() - start_time).total_seconds()

    # Print results
    print()
    print("=" * 60)
    print("✅ Migration Complete!" if not args.dry_run else "✅ Dry Run Complete!")
    print("=" * 60)
    print(f"Total historical rankings:  {stats['total_historical']:,}")
    print(f"Matched fighters:           {stats['matched_fighters']:,}")
    print(f"Unmatched fighters:         {stats['unmatched_fighters']:,}")
    print(f"Successfully inserted:      {stats['inserted']:,}")
    print(f"Duplicates skipped:         {stats['duplicates_skipped']:,}")
    print(f"Errors:                     {stats['errors']:,}")
    print(f"Duration:                   {duration:.1f}s")
    print()

    if args.dry_run:
        print("💡 Run without --dry-run to perform the actual migration")
        print()

    if stats["unmatched_fighters"] > 0:
        match_rate = (
            stats["matched_fighters"]
            / (stats["matched_fighters"] + stats["unmatched_fighters"])
        ) * 100
        print(
            f"ℹ️  Match rate: {match_rate:.1f}% ({stats['unmatched_fighters']:,} fighters not in database)"
        )
        print(
            "   This is expected - Fight Matrix includes non-UFC fighters (Bellator, Pride, etc.)"
        )
        print()


if __name__ == "__main__":
    main()
