#!/usr/bin/env python3
"""
Match BestFightOdds fighter URLs to UFC Pokedex database fighters.

This script:
1. Loads fighter URLs from scraped BFO data
2. Queries fighters from the database
3. Performs fuzzy name matching
4. Outputs a mapping file for the scraper
"""

import json
import sys
from pathlib import Path
from difflib import SequenceMatcher

import psycopg


def normalize_name(name: str) -> str:
    """Normalize fighter name for matching."""
    return name.lower().strip().replace(".", "").replace("-", " ")


def similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio()


def load_bfo_fighters(jsonl_file: Path) -> dict[str, str]:
    """Load fighter names and URLs from BFO JSONL data."""
    fighters = {}

    with jsonl_file.open() as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)

            # Extract fighter 1
            if f1 := data.get("fighter_1"):
                if name := f1.get("name"):
                    if url := f1.get("url"):
                        fighters[name] = url

            # Extract fighter 2
            if f2 := data.get("fighter_2"):
                if name := f2.get("name"):
                    if url := f2.get("url"):
                        fighters[name] = url

    return fighters


def main():
    # Load BFO fighters
    bfo_file = Path("data/raw/bfo_odds_batch.jsonl")
    if not bfo_file.exists():
        print(f"Error: {bfo_file} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Loading BFO fighters from {bfo_file}...")
    bfo_fighters = load_bfo_fighters(bfo_file)
    print(f"Found {len(bfo_fighters)} unique BFO fighters")

    # Connect to database
    print("Connecting to database...")
    conn = psycopg.connect(
        "host=localhost port=5432 dbname=ufc_pokedex user=ufc_pokedex password=ufc_pokedex"
    )

    # Get UFC fighters from database
    print("Loading fighters from database...")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT name FROM fighters ORDER BY name")
    db_fighters = [row[0] for row in cursor.fetchall()]
    print(f"Found {len(db_fighters)} unique database fighters")

    # Match fighters
    print("\nMatching fighters...")
    matches = []
    exact_matches = 0
    fuzzy_matches = 0
    no_matches = 0

    for db_name in db_fighters:
        # Try exact match first
        if db_name in bfo_fighters:
            matches.append({
                "db_name": db_name,
                "bfo_name": db_name,
                "bfo_url": bfo_fighters[db_name],
                "match_type": "exact",
                "confidence": 1.0
            })
            exact_matches += 1
            continue

        # Try fuzzy match
        best_match = None
        best_score = 0.0

        for bfo_name, bfo_url in bfo_fighters.items():
            score = similarity(db_name, bfo_name)
            if score > best_score:
                best_score = score
                best_match = (bfo_name, bfo_url)

        # Only accept fuzzy matches with >85% confidence
        if best_score > 0.85:
            matches.append({
                "db_name": db_name,
                "bfo_name": best_match[0],
                "bfo_url": best_match[1],
                "match_type": "fuzzy",
                "confidence": best_score
            })
            fuzzy_matches += 1
        else:
            no_matches += 1

    # Print statistics
    print(f"\n{'='*60}")
    print(f"Matching Results:")
    print(f"{'='*60}")
    print(f"Exact matches:  {exact_matches:4d} ({exact_matches/len(db_fighters)*100:5.1f}%)")
    print(f"Fuzzy matches:  {fuzzy_matches:4d} ({fuzzy_matches/len(db_fighters)*100:5.1f}%)")
    print(f"No match:       {no_matches:4d} ({no_matches/len(db_fighters)*100:5.1f}%)")
    print(f"Total matched:  {len(matches):4d} ({len(matches)/len(db_fighters)*100:5.1f}%)")
    print(f"{'='*60}\n")

    # Show sample fuzzy matches
    print("Sample fuzzy matches (for verification):")
    fuzzy_samples = [m for m in matches if m["match_type"] == "fuzzy"][:10]
    for m in fuzzy_samples:
        print(f"  {m['db_name']:30s} -> {m['bfo_name']:30s} ({m['confidence']:.2%})")

    # Save mapping
    output_file = Path("data/processed/bfo_fighter_url_mapping.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nSaving mapping to {output_file}...")
    with output_file.open("w") as f:
        for match in matches:
            f.write(json.dumps(match) + "\n")

    print(f"Saved {len(matches)} fighter mappings")

    conn.close()


if __name__ == "__main__":
    main()
