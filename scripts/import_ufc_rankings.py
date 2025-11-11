"""Import UFC rankings from scraped JSON file to database.

This script:
1. Loads scraped rankings from JSON
2. Fetches all fighters from database for name matching
3. Runs fuzzy name matching to find fighter IDs
4. Inserts/updates rankings in database using repository
5. Reports match statistics and unmatched fighters
"""

import asyncio
import json
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import select

from backend.db.connection import get_session
from backend.db.models import Fighter
from backend.db.repositories.ranking_repository import RankingRepository
from scraper.utils.name_matcher import FighterNameMatcher


async def load_fighters_for_matching(session):
    """Load all fighters from database for name matching.

    Returns:
        List of dicts with keys: id, name, nickname, record, division
    """
    result = await session.execute(
        select(Fighter.id, Fighter.name, Fighter.nickname, Fighter.record, Fighter.division)
    )
    rows = result.all()

    fighters_db = []
    for row in rows:
        fighters_db.append({
            "id": row.id,
            "name": row.name,
            "nickname": row.nickname,
            "record": row.record,
            "division": row.division,
        })

    return fighters_db


async def import_rankings(json_path: str, dry_run: bool = False):
    """Import rankings from JSON file to database.

    Args:
        json_path: Path to JSON file with scraped rankings
        dry_run: If True, print what would be done without making changes
    """
    # Load scraped rankings
    with open(json_path, "r") as f:
        rankings_data = json.load(f)

    print(f"Loaded {len(rankings_data)} rankings from {json_path}")

    async with get_session() as session:
        # Load fighters for name matching
        fighters_db = await load_fighters_for_matching(session)
        print(f"Loaded {len(fighters_db)} fighters from database for name matching")

        # Initialize name matcher
        matcher = FighterNameMatcher(fighters_db)

        # Match all fighter names
        fighter_names = [r["fighter_name"] for r in rankings_data]
        match_results = matcher.match_multiple(
            fighter_names,
            min_confidence=80.0,
        )

        # Print match statistics
        stats = matcher.get_match_statistics(match_results)
        print(f"\nName Matching Statistics:")
        print(f"  Total: {stats['total']}")
        print(f"  Matched: {stats['matched']} ({stats['match_rate']}%)")
        print(f"  Unmatched: {stats['unmatched']}")
        print(f"  Avg Confidence: {stats['avg_confidence']}")

        # Print unmatched fighters for manual review
        unmatched = [r for r in match_results if r["fighter_id"] is None]
        if unmatched:
            print(f"\n⚠️  {len(unmatched)} unmatched fighters (manual review required):")
            for r in unmatched:
                ranking = next(
                    (rank for rank in rankings_data if rank["fighter_name"] == r["ranking_name"]),
                    None
                )
                division = ranking["division"] if ranking else "Unknown"
                rank = ranking["rank"] if ranking else "?"
                print(f"  - {r['ranking_name']} ({division} #{rank})")
                print(f"    Reason: {r['match_reason']}")
                print(f"    Confidence: {r['confidence']}")

        if dry_run:
            print("\n🔍 DRY RUN - No database changes made")
            return

        # Insert rankings into database
        repo = RankingRepository(session)
        inserted_count = 0
        skipped_count = 0

        for i, ranking in enumerate(rankings_data):
            match_result = match_results[i]

            # Skip unmatched fighters
            if match_result["fighter_id"] is None:
                skipped_count += 1
                continue

            # Prepare ranking data for insertion
            ranking_data = {
                "fighter_id": match_result["fighter_id"],
                "division": ranking["division"],
                "rank": ranking["rank"],
                "previous_rank": ranking["previous_rank"],
                "rank_date": date.fromisoformat(ranking["rank_date"]),
                "source": ranking["source"],
                "is_interim": ranking["is_interim"],
            }

            # Upsert ranking
            await repo.upsert_ranking(ranking_data)
            inserted_count += 1

        await session.commit()

        print(f"\n✅ Import complete:")
        print(f"  Inserted/Updated: {inserted_count}")
        print(f"  Skipped (unmatched): {skipped_count}")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Import UFC rankings to database")
    parser.add_argument(
        "json_path",
        help="Path to JSON file with scraped rankings",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without making changes",
    )

    args = parser.parse_args()

    if not Path(args.json_path).exists():
        print(f"Error: File not found: {args.json_path}")
        sys.exit(1)

    await import_rankings(args.json_path, dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
