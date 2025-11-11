"""
Backfill geography data for existing fighters.

Reads scraped data from data/processed/fighters/ and updates database.
"""
import asyncio
import json
import logging
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import get_session
from backend.db.models import Fighter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill_geography():
    """Backfill geography data from scraped JSON files."""
    scraped_dir = Path("data/processed/fighters")

    if not scraped_dir.exists():
        logger.error(f"Scraped data directory not found: {scraped_dir}")
        return

    async for session in get_session():
        updated_count = 0
        skipped_count = 0

        for json_file in scraped_dir.glob("*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)

                fighter_id = json_file.stem

                # Extract geography fields
                birthplace = data.get("birthplace")
                nationality = data.get("nationality")
                fighting_out_of = data.get("fighting_out_of")

                # Skip if no geography data
                if not any([birthplace, nationality, fighting_out_of]):
                    skipped_count += 1
                    continue

                # Update fighter
                stmt = (
                    update(Fighter)
                    .where(Fighter.id == fighter_id)
                    .values(
                        birthplace=birthplace,
                        nationality=nationality,
                        fighting_out_of=fighting_out_of,
                    )
                )

                result = await session.execute(stmt)

                if result.rowcount > 0:
                    updated_count += 1
                    logger.info(
                        f"Updated {fighter_id}: "
                        f"nationality={nationality}, "
                        f"birthplace={birthplace}, "
                        f"fighting_out_of={fighting_out_of}"
                    )
                else:
                    logger.warning(f"Fighter not found in database: {fighter_id}")
                    skipped_count += 1

            except Exception as e:
                logger.error(f"Error processing {json_file}: {e}")
                skipped_count += 1

        await session.commit()

        logger.info(f"Backfill complete: {updated_count} updated, {skipped_count} skipped")


if __name__ == "__main__":
    asyncio.run(backfill_geography())
