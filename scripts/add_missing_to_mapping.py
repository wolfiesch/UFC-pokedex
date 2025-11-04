#!/usr/bin/env python
"""Add missing fighters from sherdog_matches.json to mapping."""

import json
from pathlib import Path
from rich.console import Console

console = Console()

def main():
    """Add fighters from matches that aren't in mapping."""
    console.print("[bold cyan]Adding Missing Fighters to Sherdog Mapping[/bold cyan]\n")

    # Load files
    matches_file = Path("data/processed/sherdog_matches.json")
    mapping_file = Path("data/sherdog_id_mapping.json")

    with matches_file.open() as f:
        matches = json.load(f)

    with mapping_file.open() as f:
        mapping = json.load(f)

    console.print(f"Matches file: {len(matches)} fighters")
    console.print(f"Mapping file: {len(mapping)} fighters")

    # Find fighters in matches but not in mapping
    added_count = 0

    for ufc_id, match_data in matches.items():
        if ufc_id not in mapping:
            # Check if match has Sherdog ID
            if isinstance(match_data, dict) and match_data.get("sherdog_id"):
                mapping[ufc_id] = {
                    "sherdog_id": match_data["sherdog_id"],
                    "sherdog_url": match_data.get("sherdog_url", ""),
                    "confidence": match_data.get("confidence", 0),
                    "auto_approved": match_data.get("confidence", 0) >= 70
                }
                added_count += 1

    console.print(f"\n[green]✓[/green] Added {added_count} fighters to mapping")

    # Save updated mapping
    with mapping_file.open("w") as f:
        json.dump(mapping, f, indent=2)

    console.print(f"[green]✓[/green] Saved updated mapping: {len(mapping)} total fighters")

if __name__ == "__main__":
    main()
