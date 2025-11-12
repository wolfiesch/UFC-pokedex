#!/usr/bin/env python3
"""Extract non-UFC fighters from FightMatrix historical data.

This script identifies fighters in FightMatrix rankings who are NOT in our UFC database,
providing a seed list for expanding our database to cover all MMA promotions.

Usage:
    python scripts/extract_non_ufc_fightmatrix.py
"""

import asyncio
import json
import os
from pathlib import Path

from sqlalchemy import text

from backend.db.connection import get_session


def load_latest_fightmatrix():
    """Load the most recent FightMatrix issue data."""
    fm_dir = Path("data/processed/fightmatrix_historical")

    if not fm_dir.exists():
        print(f"❌ FightMatrix directory not found: {fm_dir}")
        return None

    # Find latest issue (highest number)
    issue_files = sorted(fm_dir.glob("issue_*.json"))
    if not issue_files:
        print("❌ No FightMatrix issue files found")
        return None

    latest_file = issue_files[-1]
    print(f"📂 Loading latest FightMatrix data: {latest_file.name}")

    with open(latest_file) as f:
        data = json.load(f)

    return data


def extract_all_fighters(fightmatrix_data):
    """Extract all unique fighters from FightMatrix data.

    Returns:
        List of dicts with fighter info: name, profile_url, division, rank, points
    """
    fighters = []
    seen_names = set()

    for division_data in fightmatrix_data.get("divisions", []):
        division_name = division_data.get("division_name", "Unknown")

        for fighter in division_data.get("fighters", []):
            name = fighter.get("name")
            if not name or name in seen_names:
                continue

            seen_names.add(name)
            fighters.append({
                "name": name,
                "profile_url": fighter.get("profile_url"),
                "division": division_name,
                "rank": fighter.get("rank"),
                "points": fighter.get("points"),
            })

    return fighters


async def find_non_ufc_fighters(all_fighters):
    """Find fighters not in our UFC database.

    Args:
        all_fighters: List of fighter dicts from FightMatrix

    Returns:
        Tuple of (non_ufc_fighters, ufc_fighters, stats)
    """
    async with get_session() as session:
        # Get all UFC fighter names (case-insensitive lookup)
        result = await session.execute(text("SELECT name FROM fighters"))
        ufc_fighters_db = result.fetchall()
        ufc_names = {name.lower() for (name,) in ufc_fighters_db}

        print(f"📊 UFC database has {len(ufc_names)} fighters")

        non_ufc = []
        ufc_matched = []

        for fighter in all_fighters:
            name = fighter["name"]
            if name.lower() not in ufc_names:
                non_ufc.append(fighter)
            else:
                ufc_matched.append(fighter)

        stats = {
            "total_fightmatrix": len(all_fighters),
            "ufc_matched": len(ufc_matched),
            "non_ufc": len(non_ufc),
            "match_rate": round(len(ufc_matched) / len(all_fighters) * 100, 1) if all_fighters else 0,
        }

        return non_ufc, ufc_matched, stats


async def main():
    """Main execution."""
    print("=" * 60)
    print("EXTRACTING NON-UFC FIGHTERS FROM FIGHTMATRIX")
    print("=" * 60)
    print()

    # Load FightMatrix data
    fm_data = load_latest_fightmatrix()
    if not fm_data:
        return

    issue_date = fm_data.get("issue_date", "Unknown")
    print(f"📅 Issue date: {issue_date}")
    print()

    # Extract all fighters
    all_fighters = extract_all_fighters(fm_data)
    print(f"✅ Extracted {len(all_fighters)} unique fighters from FightMatrix")
    print()

    # Find non-UFC fighters
    non_ufc, ufc_matched, stats = await find_non_ufc_fighters(all_fighters)

    # Print statistics
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total FightMatrix fighters: {stats['total_fightmatrix']}")
    print(f"UFC matched:                {stats['ufc_matched']} ({stats['match_rate']}%)")
    print(f"Non-UFC fighters:           {stats['non_ufc']} ({100 - stats['match_rate']:.1f}%)")
    print()

    # Save non-UFC fighters
    output_file = Path("data/processed/non_ufc_fightmatrix_fighters.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump({
            "metadata": {
                "issue_date": issue_date,
                "extracted_at": fm_data.get("issue_date"),
                "stats": stats,
            },
            "fighters": non_ufc,
        }, f, indent=2)

    print(f"💾 Saved non-UFC fighters to: {output_file}")
    print()

    # Show sample fighters by division
    print("=" * 60)
    print("SAMPLE NON-UFC FIGHTERS BY DIVISION")
    print("=" * 60)

    # Group by division
    by_division = {}
    for fighter in non_ufc:
        div = fighter["division"]
        if div not in by_division:
            by_division[div] = []
        by_division[div].append(fighter)

    for division, fighters in sorted(by_division.items()):
        print(f"\n{division} ({len(fighters)} fighters):")
        # Show top 5 by rank
        sorted_fighters = sorted(fighters, key=lambda x: x["rank"] or 999)[:5]
        for f in sorted_fighters:
            rank = f["rank"] or "N/A"
            points = f["points"] or "N/A"
            print(f"  #{rank:3} - {f['name']:30} ({points} pts)")

    print()
    print("=" * 60)
    print(f"✅ COMPLETE - Ready to scrape {len(non_ufc)} non-UFC fighters from Sherdog")
    print("=" * 60)
    print()
    print("Next step:")
    print("  python scripts/search_sherdog_fightmatrix.py")
    print()


if __name__ == "__main__":
    # Ensure we're using PostgreSQL
    db_url = os.getenv("DATABASE_URL")
    if not db_url or "postgresql" not in db_url:
        print("❌ ERROR: DATABASE_URL not set or not PostgreSQL")
        print("   Run: export DATABASE_URL=postgresql+psycopg://ufc_pokedex:ufc_pokedex@localhost:5432/ufc_pokedex")
        exit(1)

    asyncio.run(main())
