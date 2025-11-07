#!/usr/bin/env python
"""
Batch processing script for fighter image face detection and cropping.

Usage:
    # Process all fighters
    python scripts/process_fighter_images.py --all

    # Process specific fighters
    python scripts/process_fighter_images.py --fighter-ids abc123,def456

    # Dry-run mode (detect only, no cropping)
    python scripts/process_fighter_images.py --all --dry-run

    # Set concurrency
    python scripts/process_fighter_images.py --all --workers 8

    # Force reprocess already cropped images
    python scripts/process_fighter_images.py --all --force
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.connection import get_session
from backend.db.models import Fighter
from backend.services.image_cropper import ImageCropper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

console = Console()


class ProcessingStats:
    """Track statistics for batch processing."""

    def __init__(self):
        self.total = 0
        self.processed = 0
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        self.high_confidence = 0  # > 0.8
        self.low_confidence = 0  # 0.5-0.8
        self.no_face = 0
        self.errors: list[tuple[str, str]] = []  # (fighter_id, error)
        self.processing_times: list[float] = []

    def add_success(self, confidence: float, processing_time: float):
        """Record a successful crop."""
        self.successful += 1
        self.processed += 1
        self.processing_times.append(processing_time)

        if confidence >= 0.8:
            self.high_confidence += 1
        else:
            self.low_confidence += 1

    def add_failure(self, reason: str, fighter_id: str | None = None):
        """Record a failed crop."""
        self.failed += 1
        self.processed += 1

        if reason.lower().find("no face") >= 0:
            self.no_face += 1

        if fighter_id:
            self.errors.append((fighter_id, reason))

    def add_skip(self):
        """Record a skipped fighter."""
        self.skipped += 1
        self.processed += 1

    def print_summary(self):
        """Print summary statistics."""
        table = Table(title="Processing Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Total Fighters", str(self.total))
        table.add_row("Processed", str(self.processed))
        table.add_row("Successful Crops", str(self.successful))
        table.add_row("Failed Crops", str(self.failed))
        table.add_row("Skipped (Already Processed)", str(self.skipped))
        table.add_row("", "")
        table.add_row("High Confidence (> 0.8)", str(self.high_confidence))
        table.add_row("Low Confidence (0.5-0.8)", str(self.low_confidence))
        table.add_row("No Face Detected", str(self.no_face))

        if self.processing_times:
            avg_time = sum(self.processing_times) / len(self.processing_times)
            min_time = min(self.processing_times)
            max_time = max(self.processing_times)
            table.add_row("", "")
            table.add_row("Avg Processing Time", f"{avg_time:.2f}s")
            table.add_row("Min Processing Time", f"{min_time:.2f}s")
            table.add_row("Max Processing Time", f"{max_time:.2f}s")

        console.print(table)

        # Print errors if any
        if self.errors:
            console.print("\n[red]Errors:[/red]")
            for fighter_id, error in self.errors[:10]:  # Show first 10
                console.print(f"  {fighter_id}: {error}")
            if len(self.errors) > 10:
                console.print(f"  ... and {len(self.errors) - 10} more")


async def get_fighters_to_process(
    session: AsyncSession,
    fighter_ids: list[str] | None = None,
    force: bool = False,
    limit: int | None = None,
) -> list[Fighter]:
    """
    Get list of fighters to process.

    Args:
        session: Database session
        fighter_ids: Optional list of specific fighter IDs
        force: If True, reprocess already cropped images
        limit: Maximum number of fighters to process

    Returns:
        List of Fighter objects
    """
    if fighter_ids:
        # Process specific fighters
        stmt = select(Fighter).where(Fighter.id.in_(fighter_ids))
    elif force:
        # Process all fighters, regardless of crop status
        stmt = select(Fighter)
    else:
        # Only process fighters without cropped images
        stmt = select(Fighter).where(Fighter.cropped_image_url.is_(None))

    if limit:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    fighters = result.scalars().all()

    return list(fighters)


def process_single_fighter(
    fighter_id: str,
    image_path: Path,
    output_path: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Process a single fighter image.

    Args:
        fighter_id: Fighter ID
        image_path: Path to original image
        output_path: Path to save cropped image
        dry_run: If True, only detect faces without cropping

    Returns:
        Dictionary with processing results
    """
    import time

    start_time = time.time()

    result = {
        "fighter_id": fighter_id,
        "success": False,
        "confidence": 0.0,
        "quality_score": 0.0,
        "cropped_path": None,
        "error": None,
        "processing_time": 0.0,
    }

    try:
        if not image_path.exists():
            result["error"] = f"Image not found: {image_path}"
            return result

        if dry_run:
            # Dry run: only detect faces
            from backend.services.face_detection import FaceDetectionService

            detector = FaceDetectionService()
            faces = detector.detect_faces(image_path)

            if faces:
                face = detector.get_primary_face(faces)
                if face:
                    import cv2

                    image = cv2.imread(str(image_path))
                    confidence = detector.calculate_confidence(face, image)
                    result["success"] = True
                    result["confidence"] = confidence
                    result["quality_score"] = confidence
            else:
                result["error"] = "No faces detected"

        else:
            # Full processing: crop and save
            cropper = ImageCropper()
            crop_result = cropper.crop_to_face(image_path, output_path)

            result["success"] = crop_result.success
            result["confidence"] = crop_result.confidence
            result["quality_score"] = crop_result.quality_score
            result["cropped_path"] = crop_result.cropped_path
            result["error"] = crop_result.error_message

    except (OSError, ValueError, RuntimeError) as e:
        logger.error(f"Error processing fighter {fighter_id}: {e}")
        result["error"] = str(e)

    finally:
        result["processing_time"] = time.time() - start_time

    return result


async def update_fighter_crop_metadata(
    session: AsyncSession,
    fighter_id: str,
    cropped_path: str | None,
    confidence: float,
):
    """
    Update fighter database record with crop metadata.

    Args:
        session: Database session
        fighter_id: Fighter ID
        cropped_path: Path to cropped image (relative)
        confidence: Face detection confidence
    """
    stmt = select(Fighter).where(Fighter.id == fighter_id)
    result = await session.execute(stmt)
    fighter = result.scalar_one_or_none()

    if fighter:
        fighter.cropped_image_url = cropped_path
        fighter.face_detection_confidence = confidence
        fighter.crop_processed_at = datetime.utcnow()
        # No need to commit here - caller will handle it


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Batch process fighter images for face detection and cropping"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all fighters",
    )
    parser.add_argument(
        "--fighter-ids",
        type=str,
        help="Comma-separated list of fighter IDs to process",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect faces only, don't crop or save",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess already cropped images",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of fighters to process",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate arguments
    if not args.all and not args.fighter_ids:
        console.print("[red]Error: Must specify --all or --fighter-ids[/red]")
        sys.exit(1)

    # Parse fighter IDs if provided
    fighter_ids = None
    if args.fighter_ids:
        fighter_ids = [fid.strip() for fid in args.fighter_ids.split(",")]

    # Get fighters to process
    console.print("[cyan]Loading fighters from database...[/cyan]")
    async with get_session() as session:
        fighters = await get_fighters_to_process(
            session, fighter_ids, args.force, args.limit
        )

    if not fighters:
        console.print("[yellow]No fighters to process[/yellow]")
        return

    stats = ProcessingStats()
    stats.total = len(fighters)

    console.print(f"[green]Found {len(fighters)} fighters to process[/green]")

    # Prepare image paths
    base_image_dir = Path("data/images/fighters")
    base_cropped_dir = Path("data/images/fighters/cropped")
    base_cropped_dir.mkdir(parents=True, exist_ok=True)

    tasks = []
    for fighter in fighters:
        # Find fighter image
        image_path = None
        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            candidate = base_image_dir / f"{fighter.id}{ext}"
            if candidate.exists():
                image_path = candidate
                break

        if not image_path:
            logger.warning(f"No image found for fighter {fighter.id} ({fighter.name})")
            stats.add_failure("No image file found", fighter.id)
            continue

        output_path = base_cropped_dir / f"{fighter.id}.jpg"

        # Skip if already processed and not forcing
        if not args.force and fighter.cropped_image_url and not args.dry_run:
            stats.add_skip()
            continue

        tasks.append({
            "fighter": fighter,
            "image_path": image_path,
            "output_path": output_path,
        })

    if not tasks:
        console.print("[yellow]No images to process (all already processed)[/yellow]")
        stats.print_summary()
        return

    console.print(f"[cyan]Processing {len(tasks)} images...[/cyan]")

    # Process with progress bar
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_progress = progress.add_task(
            "Processing images...",
            total=len(tasks),
        )

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_task = {
                executor.submit(
                    process_single_fighter,
                    task["fighter"].id,
                    task["image_path"],
                    task["output_path"],
                    args.dry_run,
                ): task
                for task in tasks
            }

            for future in as_completed(future_to_task):
                task_data = future_to_task[future]
                fighter = task_data["fighter"]

                try:
                    result = future.result()

                    if result["success"]:
                        stats.add_success(
                            result["confidence"],
                            result["processing_time"],
                        )

                        # Update database if not dry run
                        if not args.dry_run:
                            async with get_session() as session:
                                await update_fighter_crop_metadata(
                                    session,
                                    fighter.id,
                                    f"images/fighters/cropped/{fighter.id}.jpg",
                                    result["confidence"],
                                )
                                await session.commit()

                    else:
                        stats.add_failure(
                            result["error"] or "Unknown error",
                            fighter.id,
                        )

                except (OSError, ValueError, RuntimeError) as e:
                    logger.error(f"Error processing {fighter.id}: {e}")
                    stats.add_failure(str(e), fighter.id)

                progress.advance(task_progress)

    # Print summary
    console.print("\n")
    stats.print_summary()

    # Success message
    if stats.successful > 0:
        console.print(
            f"\n[green]Successfully processed {stats.successful} images![/green]"
        )
    if stats.failed > 0:
        console.print(
            f"[yellow]{stats.failed} images failed processing[/yellow]"
        )


if __name__ == "__main__":
    asyncio.run(main())
