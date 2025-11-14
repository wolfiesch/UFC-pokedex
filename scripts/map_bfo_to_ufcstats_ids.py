#!/usr/bin/env python3
"""Map BFO fighter IDs to UFC Stats IDs using name matching."""

import asyncio
import json
import logging
from pathlib import Path
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import create_engine, create_session_factory
from backend.db.models import Fighter

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    """Normalize fighter name for matching."""
    return name.lower().strip().replace(".", "").replace("-", " ").replace("  ", " ")


def name_similarity(name1: str, name2: str) -> float:
    """Calculate similarity ratio between two names."""
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)
    return SequenceMatcher(None, norm1, norm2).ratio()


async def main():
    # Load UFC Stats fighters from database
    engine = create_engine()
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        result = await session.execute(select(Fighter.id, Fighter.name))
        ufc_fighters = {normalize_name(name): fighter_id for fighter_id, name in result.all()}

    await engine.dispose()

    logger.info(f"Loaded {len(ufc_fighters)} UFC Stats fighters from database")

    # Load BFO fighter data
    bfo_file = Path("data/raw/bfo_fighter_mean_odds.jsonl")
    bfo_fighters = {}  # {bfo_id: fighter_name}

    with open(bfo_file) as f:
        for line in f:
            record = json.loads(line)
            bfo_id = record["fighter_id"]
            fighter_name = record.get("fighter_name", "")
            if bfo_id not in bfo_fighters:
                bfo_fighters[bfo_id] = fighter_name

    logger.info(f"Found {len(bfo_fighters)} unique BFO fighter IDs")

    # Create mapping
    mapping = {}  # {bfo_id: ufc_stats_id}
    unmatched = []

    for bfo_id, bfo_name in bfo_fighters.items():
        norm_bfo = normalize_name(bfo_name)

        # Try exact match first
        if norm_bfo in ufc_fighters:
            mapping[bfo_id] = ufc_fighters[norm_bfo]
            continue

        # Try fuzzy match
        best_match = None
        best_score = 0.0

        for ufc_name, ufc_id in ufc_fighters.items():
            score = name_similarity(norm_bfo, ufc_name)
            if score > best_score:
                best_score = score
                best_match = (ufc_name, ufc_id)

        if best_score >= 0.85:  # 85% similarity threshold
            mapping[bfo_id] = best_match[1]
        else:
            unmatched.append((bfo_id, bfo_name, best_score, best_match[0] if best_match else "N/A"))

    logger.info(f"Matched {len(mapping)} BFO IDs to UFC Stats IDs")
    logger.info(f"Unmatched: {len(unmatched)} BFO fighters")

    # Save mapping
    output_file = Path("data/processed/bfo_to_ufcstats_id_mapping.json")
    with open(output_file, "w") as f:
        json.dump(mapping, f, indent=2)

    logger.info(f"Saved mapping to {output_file}")

    # Save unmatched for review
    if unmatched:
        unmatched_file = Path("data/processed/bfo_unmatched_fighters.jsonl")
        with open(unmatched_file, "w") as f:
            for bfo_id, name, score, best_match in unmatched:
                f.write(json.dumps({
                    "bfo_id": bfo_id,
                    "bfo_name": name,
                    "best_match_score": score,
                    "best_match_name": best_match
                }) + "\n")
        logger.info(f"Saved {len(unmatched)} unmatched fighters to {unmatched_file}")


if __name__ == "__main__":
    asyncio.run(main())
