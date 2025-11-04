#!/usr/bin/env python3
"""Filter fighters_list.jsonl to only include fighters without detail JSON files."""

from __future__ import annotations

import json
from pathlib import Path


def main():
    """Filter to only missing fighters."""
    fighters_list = Path("data/processed/fighters_list.jsonl")
    fighters_dir = Path("data/processed/fighters")
    output_file = Path("data/processed/fighters_missing.jsonl")

    if not fighters_list.exists():
        print(f"Error: {fighters_list} not found")
        return

    # Get set of already scraped fighter IDs
    scraped_ids = {f.stem for f in fighters_dir.glob("*.json")}
    print(f"Found {len(scraped_ids)} already scraped fighters")

    # Filter to missing fighters
    missing_count = 0
    with fighters_list.open() as infile, output_file.open("w") as outfile:
        for line in infile:
            fighter = json.loads(line)
            # Extract fighter ID from detail_url
            # e.g., "http://ufcstats.com/fighter-details/abc123" -> "abc123"
            fighter_id = fighter["detail_url"].rstrip("/").split("/")[-1]

            if fighter_id not in scraped_ids:
                outfile.write(line)
                missing_count += 1

    print(f"Found {missing_count} missing fighters")
    print(f"Written to {output_file}")

    if missing_count == 0:
        print("✅ All fighters already scraped!")
    else:
        print(f"\nTo scrape missing fighters, run:")
        print(f'  .venv/bin/scrapy crawl fighter_detail -a input_file="{output_file}"')


if __name__ == "__main__":
    main()
