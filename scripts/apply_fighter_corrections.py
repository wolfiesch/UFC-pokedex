#!/usr/bin/env python3
"""
Apply manual corrections to BFO fighter URL mapping.
"""

import json
from pathlib import Path

# Load manual corrections
corrections_file = Path("data/processed/bfo_fighter_manual_corrections.jsonl")
corrections = {}

with corrections_file.open() as f:
    for line in f:
        if not line.strip():
            continue
        correction = json.loads(line)
        corrections[correction["db_name"]] = correction

# Load original mapping
mapping_file = Path("data/processed/bfo_fighter_url_mapping.jsonl")
original_matches = []

with mapping_file.open() as f:
    for line in f:
        if not line.strip():
            continue
        original_matches.append(json.loads(line))

# Apply corrections
corrected_matches = []
rejected_count = 0
corrected_count = 0
kept_exact_count = 0
kept_fuzzy_count = 0

for match in original_matches:
    db_name = match["db_name"]

    # Check if there's a manual correction
    if db_name in corrections:
        correction = corrections[db_name]

        if correction["action"] == "reject":
            rejected_count += 1
            print(f"REJECTED: {db_name} -> {match['bfo_name']} ({correction['reason']})")
            continue  # Skip this match

        elif correction["action"] == "accept":
            # Update the match with corrected BFO name if provided
            if "bfo_name" in correction:
                match["bfo_name"] = correction["bfo_name"]
            match["manually_verified"] = True
            match["verification_note"] = correction["reason"]
            corrected_matches.append(match)
            corrected_count += 1
            print(f"CORRECTED: {db_name} -> {match['bfo_name']} ({correction['reason']})")
    else:
        # Keep exact matches as-is
        if match["match_type"] == "exact":
            corrected_matches.append(match)
            kept_exact_count += 1
        # Keep fuzzy matches with perfect confidence (1.0) that weren't rejected
        elif match["confidence"] == 1.0:
            corrected_matches.append(match)
            kept_fuzzy_count += 1

# Save corrected mapping
output_file = Path("data/processed/bfo_fighter_url_mapping_corrected.jsonl")
with output_file.open("w") as f:
    for match in corrected_matches:
        f.write(json.dumps(match) + "\n")

print(f"\n{'='*60}")
print(f"Correction Summary:")
print(f"{'='*60}")
print(f"Original matches:    {len(original_matches):4d}")
print(f"Kept exact:          {kept_exact_count:4d}")
print(f"Kept fuzzy (1.0):    {kept_fuzzy_count:4d}")
print(f"Manually corrected:  {corrected_count:4d}")
print(f"Rejected:            {rejected_count:4d}")
print(f"Final matches:       {len(corrected_matches):4d}")
print(f"{'='*60}")
print(f"\nSaved to: {output_file}")
