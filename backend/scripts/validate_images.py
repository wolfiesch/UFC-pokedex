#!/usr/bin/env python3
"""CLI command to validate all fighter images.

This script processes all fighter images in the database, performs:
- Face detection
- Quality analysis (resolution, blur, brightness)
- Duplicate detection via perceptual hashing

Results are stored in the database for later querying via API.

Usage:
    python -m backend.scripts.validate_images [--batch-size 100] [--force]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, UTC
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import get_async_session_context
from backend.db.models import Fighter
from backend.services.image_validator import ImageValidator

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def validate_all_images(
    batch_size: int = 100, force: bool = False, limit: int | None = None
) -> None:
    """Validate all fighter images and store results in database.

    Args:
        batch_size: Number of fighters to process per database commit.
        force: If True, re-validate already validated images.
        limit: If set, only validate this many images (for testing).
    """
    logger.info("Starting image validation process...")

    # Initialize validator
    validator = ImageValidator()

    # Track statistics
    stats = {
        "total": 0,
        "validated": 0,
        "skipped": 0,
        "no_image": 0,
        "errors": 0,
        "flags": {
            "low_resolution": 0,
            "no_face_detected": 0,
            "multiple_faces": 0,
            "blurry_image": 0,
            "too_dark": 0,
            "too_bright": 0,
        },
    }

    # Store perceptual hashes for duplicate detection
    fighter_hashes: dict[str, str] = {}

    async with get_async_session_context() as session:
        # Get all fighters
        query = select(Fighter)
        if limit:
            query = query.limit(limit)

        result = await session.execute(query)
        fighters = result.scalars().all()

        logger.info(f"Found {len(fighters)} fighters to validate")

        # Process in batches
        for i in range(0, len(fighters), batch_size):
            batch = fighters[i : i + batch_size]

            for fighter in batch:
                stats["total"] += 1

                # Skip if already validated and not forcing
                if not force and fighter.image_validated_at is not None:
                    stats["skipped"] += 1
                    continue

                # Validate image
                result = validator.validate_image(fighter.id)

                if result is None:
                    stats["no_image"] += 1
                    logger.debug(f"No image found for fighter {fighter.id} ({fighter.name})")
                    continue

                try:
                    # Update fighter record
                    fighter.image_quality_score = result.quality_score
                    fighter.image_resolution_width = result.width
                    fighter.image_resolution_height = result.height
                    fighter.has_face_detected = result.has_face
                    fighter.face_count = result.face_count
                    fighter.image_validation_flags = result.flags
                    fighter.face_encoding = result.face_encoding
                    fighter.image_validated_at = datetime.now(UTC)

                    stats["validated"] += 1

                    # Store hash for duplicate detection
                    fighter_hashes[fighter.id] = result.perceptual_hash

                    # Count flags
                    for flag_key in result.flags:
                        if flag_key in stats["flags"]:
                            stats["flags"][flag_key] += 1

                    if stats["validated"] % 50 == 0:
                        logger.info(f"Validated {stats['validated']} images...")

                except Exception as e:
                    stats["errors"] += 1
                    logger.error(f"Error updating fighter {fighter.id}: {e}")

            # Commit batch
            try:
                await session.commit()
                logger.info(f"Committed batch {i // batch_size + 1}")
            except Exception as e:
                logger.error(f"Error committing batch: {e}")
                await session.rollback()

        # Find duplicates
        logger.info("Detecting duplicate images...")
        duplicates = validator.find_duplicates(fighter_hashes)

        if duplicates:
            logger.info(f"Found {len(duplicates)} fighters with potential duplicates")

            # Update fighters with duplicate flags
            for fighter_id, duplicate_ids in duplicates.items():
                query = select(Fighter).where(Fighter.id == fighter_id)
                result = await session.execute(query)
                fighter = result.scalar_one_or_none()

                if fighter:
                    flags = fighter.image_validation_flags or {}
                    flags["potential_duplicates"] = duplicate_ids
                    fighter.image_validation_flags = flags

            await session.commit()

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total fighters: {stats['total']}")
    logger.info(f"Validated: {stats['validated']}")
    logger.info(f"Skipped (already validated): {stats['skipped']}")
    logger.info(f"No image found: {stats['no_image']}")
    logger.info(f"Errors: {stats['errors']}")
    logger.info("\nValidation Flags:")
    for flag, count in stats["flags"].items():
        if count > 0:
            logger.info(f"  {flag}: {count}")
    logger.info(f"\nPotential duplicates: {len(duplicates)}")
    logger.info("=" * 60)


async def get_validation_stats(session: AsyncSession) -> dict:
    """Get statistics about validated images."""
    query = select(Fighter)
    result = await session.execute(query)
    fighters = result.scalars().all()

    stats = {
        "total": len(fighters),
        "validated": 0,
        "with_faces": 0,
        "without_faces": 0,
        "low_quality": 0,
        "with_flags": 0,
    }

    for fighter in fighters:
        if fighter.image_validated_at:
            stats["validated"] += 1

            if fighter.has_face_detected:
                stats["with_faces"] += 1
            else:
                stats["without_faces"] += 1

            if fighter.image_quality_score and fighter.image_quality_score < 50:
                stats["low_quality"] += 1

            if fighter.image_validation_flags:
                stats["with_flags"] += 1

    return stats


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate all fighter images")
    parser.add_argument(
        "--batch-size", type=int, default=100, help="Batch size for database commits"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-validate already validated images",
    )
    parser.add_argument("--limit", type=int, help="Only validate this many images (for testing)")
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show validation statistics and exit",
    )

    args = parser.parse_args()

    if args.stats:
        async with get_async_session_context() as session:
            stats = await get_validation_stats(session)
            print("\nValidation Statistics:")
            print("=" * 40)
            for key, value in stats.items():
                print(f"{key}: {value}")
            print("=" * 40)
    else:
        await validate_all_images(batch_size=args.batch_size, force=args.force, limit=args.limit)


if __name__ == "__main__":
    asyncio.run(main())
