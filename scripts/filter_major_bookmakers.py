#!/usr/bin/env python3
"""
Filter scraped odds data to only include major bookmakers.

This removes deprecated bookmakers (IDs 1, 2) that have suspicious odds
and keeps only the active major bookmakers displayed on the site.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path to import bookmaker_mapping
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.bookmaker_mapping import (
    MAJOR_BOOKMAKERS,
    TIER_1_BOOKMAKERS,
    filter_major_bookmakers,
    filter_tier1_bookmakers,
)


def filter_odds_file(
    input_file: str,
    output_file: str,
    tier1_only: bool = False,
):
    """
    Filter odds file to only include major bookmakers.

    Args:
        input_file: Path to input JSONL file
        output_file: Path to output JSONL file
        tier1_only: If True, only keep tier 1 bookmakers
    """
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        print(f"❌ Input file not found: {input_file}")
        return

    print(f"📊 Filtering odds data...")
    print(f"   Input: {input_file}")
    print(f"   Output: {output_file}")
    if tier1_only:
        print(f"   Filter: Tier 1 only (FanDuel, DraftKings, BetMGM, Caesars)")
        filter_func = filter_tier1_bookmakers
    else:
        print(f"   Filter: All major bookmakers (9 total)")
        filter_func = filter_major_bookmakers
    print()

    total_records = 0
    records_with_odds = 0
    total_bookmakers_before = 0
    total_bookmakers_after = 0

    with input_path.open() as infile, output_path.open('w') as outfile:
        for line in infile:
            data = json.loads(line)
            total_records += 1

            # Filter bookmakers
            original_count = data['odds']['count']
            total_bookmakers_before += original_count

            data['odds'] = filter_func(data['odds'])
            filtered_count = data['odds']['count']
            total_bookmakers_after += filtered_count

            if filtered_count > 0:
                records_with_odds += 1

            # Write filtered record
            outfile.write(json.dumps(data) + '\n')

    print(f"✅ Filtering complete!")
    print()
    print(f"📈 Statistics:")
    print(f"   Total records: {total_records}")
    print(f"   Records with odds: {records_with_odds} ({records_with_odds/total_records*100:.1f}%)")
    print(f"   Bookmakers before: {total_bookmakers_before}")
    print(f"   Bookmakers after: {total_bookmakers_after}")
    print(f"   Removed: {total_bookmakers_before - total_bookmakers_after}")
    print()

    # Show sample
    print(f"🔍 Sample record:")
    with output_path.open() as f:
        for line in f:
            data = json.loads(line)
            if data['odds']['count'] > 0:
                print(f"   Event: {data['event_title']}")
                print(f"   Fight: {data['fighter_1']['name']} vs {data['fighter_2']['name']}")
                print(f"   Bookmakers: {data['odds']['count']}")
                for bm in data['odds']['bookmakers'][:3]:
                    print(f"      - ID {bm['bookmaker_id']}: {bm['fighter_1_odds']} / {bm['fighter_2_odds']}")
                break


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Filter odds data to major bookmakers")
    parser.add_argument(
        "--input",
        default="data/raw/bfo_odds_batch.jsonl",
        help="Input JSONL file",
    )
    parser.add_argument(
        "--output",
        default="data/raw/bfo_odds_filtered.jsonl",
        help="Output JSONL file",
    )
    parser.add_argument(
        "--tier1-only",
        action="store_true",
        help="Only keep tier 1 bookmakers (FanDuel, DraftKings, BetMGM, Caesars)",
    )

    args = parser.parse_args()

    filter_odds_file(args.input, args.output, args.tier1_only)
