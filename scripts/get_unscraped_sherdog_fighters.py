#!/usr/bin/env python3
"""
Identify fighters that haven't been scraped from Sherdog yet.

This script compares the target fighter list with already scraped fighters
and outputs the names of fighters that still need to be scraped.
"""
import json
import sys
from pathlib import Path


def get_target_fighters(input_file: Path) -> set[str]:
    """Load target fighters from JSON file."""
    with input_file.open() as f:
        data = json.load(f)
        # Handle both old format (array) and new format (object with fighters key)
        if isinstance(data, list):
            fighters = data
        elif "fighters" in data:
            fighters = data["fighters"]
        else:
            raise ValueError(f"Unexpected JSON format in {input_file}")

        return {fighter["name"] for fighter in fighters}


def get_scraped_fighters(output_file: Path) -> set[str]:
    """Load already scraped fighters from JSONL file."""
    if not output_file.exists():
        return set()

    scraped = set()
    with output_file.open() as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                # Handle both 'fighter_name' and 'name' keys
                fighter_name = data.get("fighter_name") or data.get("name")
                if fighter_name:
                    scraped.add(fighter_name)

    return scraped


def main():
    # Paths
    project_root = Path(__file__).parent.parent
    target_file = project_root / "data/processed/non_ufc_fightmatrix_fighters.json"
    scraped_file = project_root / "data/processed/sherdog_fight_histories.jsonl"

    # Load data
    target_fighters = get_target_fighters(target_file)
    scraped_fighters = get_scraped_fighters(scraped_file)

    # Find unscraped fighters
    unscraped = target_fighters - scraped_fighters

    # Output results
    if not unscraped:
        print("✅ All fighters have been scraped!", file=sys.stderr)
        sys.exit(0)

    print(f"Found {len(unscraped)} unscraped fighters out of {len(target_fighters)} total", file=sys.stderr)
    print(f"Already scraped: {len(scraped_fighters)}", file=sys.stderr)
    print("", file=sys.stderr)

    # Print unscraped fighter names (one per line) to stdout
    for name in sorted(unscraped):
        print(name)


if __name__ == "__main__":
    main()
