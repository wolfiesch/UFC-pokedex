#!/usr/bin/env python
"""Check which missing fighters are in Sherdog mapping."""

import json
from pathlib import Path
from rich.console import Console

console = Console()

# Load missing fighters
missing_file = Path("/tmp/fighters_no_images.txt")
missing_ids = {line.strip() for line in missing_file.read_text().splitlines() if line.strip()}

console.print(f"Missing images: {len(missing_ids)} fighters")

# Load Sherdog mapping
mapping_file = Path("data/sherdog_id_mapping.json")
with mapping_file.open() as f:
    sherdog_mapping = json.load(f)

console.print(f"Sherdog mapping: {len(sherdog_mapping)} fighters\n")

# Find intersection
in_mapping = []
for fighter_id in missing_ids:
    if fighter_id in sherdog_mapping:
        in_mapping.append(fighter_id)

console.print(f"[green]✓[/green] {len(in_mapping)} missing fighters ARE in Sherdog mapping")
console.print(f"[yellow]⚠[/yellow] {len(missing_ids) - len(in_mapping)} missing fighters NOT in Sherdog mapping\n")

if in_mapping:
    console.print("Fighters in mapping (sample):")
    for fid in in_mapping[:10]:
        url = sherdog_mapping[fid].get("sherdog_url", "")
        console.print(f"  - {fid}: {url}")
