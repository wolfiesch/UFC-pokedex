#!/usr/bin/env python3
"""Update cleaned odds data with UFC Stats fighter IDs."""

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    # Load mapping
    mapping_file = Path("data/processed/bfo_to_ufcstats_id_mapping.json")
    with open(mapping_file) as f:
        bfo_to_ufc = json.load(f)

    logger.info(f"Loaded {len(bfo_to_ufc)} ID mappings")

    # Process cleaned odds data
    input_file = Path("data/processed/bfo_fighter_mean_odds_clean.jsonl")
    output_file = Path("data/processed/bfo_fighter_mean_odds_clean_remapped.jsonl")

    processed = 0
    skipped = 0

    with open(input_file) as infile, open(output_file, "w") as outfile:
        for line in infile:
            record = json.loads(line)
            bfo_id = record["fighter_id"]

            # Map to UFC Stats ID
            ufc_id = bfo_to_ufc.get(bfo_id)
            if not ufc_id:
                skipped += 1
                logger.warning(f"No mapping for BFO ID {bfo_id}, skipping")
                continue

            # Update fighter_id and regenerate odds ID
            record["fighter_id"] = ufc_id

            # Regenerate odds ID with new fighter_id
            import hashlib
            key = f"{ufc_id}|{record['opponent_name']}|{record['event_name']}"
            record["id"] = f"odds_{hashlib.md5(key.encode()).hexdigest()}"

            outfile.write(json.dumps(record) + "\n")
            processed += 1

    logger.info(f"Processed {processed} records, skipped {skipped}")
    logger.info(f"Wrote remapped data to {output_file}")


if __name__ == "__main__":
    main()
