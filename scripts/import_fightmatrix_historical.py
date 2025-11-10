"""
Import Fight Matrix Historical Rankings into Database

Loads scraped historical rankings from JSON files and imports them into
a new database table for historical ranking snapshots.

Database Schema (New Table):
    historical_rankings:
        - id (UUID, primary key)
        - issue_number (int)
        - issue_date (date)
        - division_code (int)
        - division_name (str)
        - fighter_name (str)
        - rank (int)
        - points (int)
        - movement (str, nullable)
        - profile_url (str)
        - scraped_at (datetime)

Usage:
    python scripts/import_fightmatrix_historical.py
    python scripts/import_fightmatrix_historical.py --file issue_996_11-02-2025.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Import database connection
from backend.db.connection import get_engine, get_async_session


HISTORICAL_DIR = Path("data/processed/fightmatrix_historical")


def parse_issue_date(date_str: str) -> str:
    """
    Convert Fight Matrix date format to ISO date.

    Args:
        date_str: Date in "MM/DD/YYYY" format

    Returns:
        ISO date string "YYYY-MM-DD"
    """
    try:
        dt = datetime.strptime(date_str, "%m/%d/%Y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return date_str


def create_historical_rankings_table(engine):
    """
    Create historical_rankings table if it doesn't exist.
    """
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS historical_rankings (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        issue_number INTEGER NOT NULL,
        issue_date DATE NOT NULL,
        division_code INTEGER NOT NULL,
        division_name VARCHAR(50) NOT NULL,
        fighter_name VARCHAR(255) NOT NULL,
        rank INTEGER NOT NULL,
        points INTEGER NOT NULL,
        movement VARCHAR(10),
        profile_url VARCHAR(500),
        scraped_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        -- Indexes for common queries
        CONSTRAINT unique_ranking UNIQUE (issue_number, division_code, rank)
    );

    CREATE INDEX IF NOT EXISTS idx_historical_rankings_fighter
        ON historical_rankings(fighter_name);

    CREATE INDEX IF NOT EXISTS idx_historical_rankings_division
        ON historical_rankings(division_code);

    CREATE INDEX IF NOT EXISTS idx_historical_rankings_issue
        ON historical_rankings(issue_number);

    CREATE INDEX IF NOT EXISTS idx_historical_rankings_date
        ON historical_rankings(issue_date DESC);
    """

    with engine.connect() as conn:
        for statement in create_table_sql.strip().split(';'):
            if statement.strip():
                conn.execute(text(statement))
        conn.commit()

    print("✓ Historical rankings table ready")


def import_issue_file(file_path: Path, engine) -> Dict:
    """
    Import a single issue file into the database.

    Args:
        file_path: Path to issue JSON file
        engine: SQLAlchemy engine

    Returns:
        Dict with import stats
    """
    print(f"📄 Importing {file_path.name}...")

    with open(file_path, 'r') as f:
        data = json.load(f)

    issue_number = data['issue_number']
    issue_date_str = data['issue_date']
    issue_date = parse_issue_date(issue_date_str)

    stats = {
        'file': file_path.name,
        'issue_number': issue_number,
        'issue_date': issue_date_str,
        'divisions': 0,
        'fighters_imported': 0,
        'duplicates_skipped': 0,
        'errors': 0
    }

    with engine.connect() as conn:
        for division_data in data['divisions']:
            stats['divisions'] += 1
            division_code = division_data['division']
            division_name = division_data['division_name']
            scraped_at = division_data.get('scraped_at', datetime.utcnow().isoformat())

            for fighter in division_data['fighters']:
                try:
                    # Check if already exists
                    check_sql = text("""
                        SELECT COUNT(*) as count
                        FROM historical_rankings
                        WHERE issue_number = :issue_number
                          AND division_code = :division_code
                          AND rank = :rank
                    """)

                    result = conn.execute(
                        check_sql,
                        {
                            'issue_number': issue_number,
                            'division_code': division_code,
                            'rank': fighter['rank']
                        }
                    ).fetchone()

                    if result[0] > 0:
                        stats['duplicates_skipped'] += 1
                        continue

                    # Insert new record
                    insert_sql = text("""
                        INSERT INTO historical_rankings (
                            id, issue_number, issue_date, division_code,
                            division_name, fighter_name, rank, points,
                            movement, profile_url, scraped_at
                        ) VALUES (
                            :id, :issue_number, :issue_date, :division_code,
                            :division_name, :fighter_name, :rank, :points,
                            :movement, :profile_url, :scraped_at
                        )
                    """)

                    conn.execute(
                        insert_sql,
                        {
                            'id': str(uuid4()),
                            'issue_number': issue_number,
                            'issue_date': issue_date,
                            'division_code': division_code,
                            'division_name': division_name,
                            'fighter_name': fighter['name'],
                            'rank': fighter['rank'],
                            'points': fighter['points'],
                            'movement': fighter.get('movement'),
                            'profile_url': fighter.get('profile_url'),
                            'scraped_at': scraped_at
                        }
                    )

                    stats['fighters_imported'] += 1

                except Exception as e:
                    print(f"   ⚠️  Error importing {fighter.get('name', 'unknown')}: {e}")
                    stats['errors'] += 1

        conn.commit()

    print(f"   ✓ Imported {stats['fighters_imported']} fighters "
          f"({stats['duplicates_skipped']} duplicates, {stats['errors']} errors)")

    return stats


def import_all_files(engine) -> None:
    """
    Import all issue files from the historical directory.
    """
    if not HISTORICAL_DIR.exists():
        print(f"❌ Historical data directory not found: {HISTORICAL_DIR}")
        return

    issue_files = sorted(HISTORICAL_DIR.glob("issue_*.json"))

    if not issue_files:
        print(f"⚠️  No issue files found in {HISTORICAL_DIR}")
        return

    print(f"📦 Found {len(issue_files)} issue files to import")
    print()

    total_stats = {
        'files': 0,
        'divisions': 0,
        'fighters_imported': 0,
        'duplicates_skipped': 0,
        'errors': 0
    }

    for file_path in issue_files:
        stats = import_issue_file(file_path, engine)
        total_stats['files'] += 1
        total_stats['divisions'] += stats['divisions']
        total_stats['fighters_imported'] += stats['fighters_imported']
        total_stats['duplicates_skipped'] += stats['duplicates_skipped']
        total_stats['errors'] += stats['errors']

    print()
    print(f"✅ Import complete!")
    print(f"   Files processed: {total_stats['files']}")
    print(f"   Divisions: {total_stats['divisions']}")
    print(f"   Fighters imported: {total_stats['fighters_imported']}")
    print(f"   Duplicates skipped: {total_stats['duplicates_skipped']}")
    print(f"   Errors: {total_stats['errors']}")


def main():
    parser = argparse.ArgumentParser(
        description='Import Fight Matrix historical rankings into database'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='Import a specific file (e.g., issue_996_11-02-2025.json)'
    )
    parser.add_argument(
        '--create-table-only',
        action='store_true',
        help='Only create the table, don\'t import data'
    )

    args = parser.parse_args()

    print("🚀 Fight Matrix Historical Rankings Importer")
    print()

    # Get database engine (sync)
    # For imports, we'll use a synchronous connection
    import os
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        print("   Export DATABASE_URL or update .env file")
        return

    # Convert async URL to sync if needed
    if database_url.startswith("postgresql+psycopg://"):
        database_url = database_url.replace(
            "postgresql+psycopg://",
            "postgresql+psycopg2://"
        )

    engine = create_engine(database_url)

    # Create table
    create_historical_rankings_table(engine)

    if args.create_table_only:
        print("✓ Table created, exiting")
        return

    print()

    # Import data
    if args.file:
        file_path = HISTORICAL_DIR / args.file
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return
        import_issue_file(file_path, engine)
    else:
        import_all_files(engine)


if __name__ == "__main__":
    main()
