#!/usr/bin/env python
"""Update fighter database with Sherdog IDs and image URLs."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import get_session
from backend.db.models import Fighter

# Load environment variables
load_dotenv()

console = Console()


async def update_fighter_images():
    """Update fighters with Sherdog IDs and image paths."""
    # Load mapping file
    mapping_file = Path("data/sherdog_id_mapping.json")
    if not mapping_file.exists():
        console.print(f"[red]Error:[/red] Mapping file not found: {mapping_file}")
        console.print("Please run: make verify-sherdog-matches first")
        return

    # Load image metadata
    images_file = Path("data/processed/sherdog_images.json")
    if not images_file.exists():
        console.print(f"[yellow]Warning:[/yellow] Images file not found: {images_file}")
        console.print("Image paths will not be updated. Run: make scrape-sherdog-images first")
        image_metadata = {}
    else:
        with images_file.open() as f:
            image_metadata = json.load(f)

    # Load Sherdog ID mapping
    with mapping_file.open() as f:
        mapping = json.load(f)

    console.print(f"Loaded mapping for {len(mapping)} fighters")
    console.print(f"Loaded image metadata for {len(image_metadata)} fighters")

    # Update database
    updated_count = 0
    skipped_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Updating fighters...", total=len(mapping))

        async with get_session() as session:
            session: AsyncSession

            for ufc_id, sherdog_data in mapping.items():
                sherdog_id = sherdog_data.get("sherdog_id")

                if not sherdog_id:
                    skipped_count += 1
                    progress.advance(task)
                    continue

                # Get image path if available
                image_path = None
                if ufc_id in image_metadata:
                    # Store relative path from project root
                    full_path = Path(image_metadata[ufc_id]["image_path"])
                    if full_path.exists():
                        # Store as relative path: images/fighters/{id}.jpg
                        image_path = f"images/fighters/{full_path.name}"

                # Update fighter record
                stmt = (
                    update(Fighter)
                    .where(Fighter.id == ufc_id)
                    .values(
                        sherdog_id=sherdog_id,
                        image_url=image_path,
                        image_scraped_at=datetime.utcnow(),
                    )
                )

                await session.execute(stmt)
                updated_count += 1
                progress.advance(task)

            # Commit all updates
            await session.commit()

    console.print(f"\n[green]✓[/green] Updated {updated_count} fighters")

    if skipped_count > 0:
        console.print(f"[yellow]⚠[/yellow] Skipped {skipped_count} fighters (no Sherdog ID)")

    # Show image stats
    fighters_with_images = len(image_metadata)
    fighters_without_images = updated_count - fighters_with_images

    if fighters_without_images > 0:
        console.print(
            f"[yellow]⚠[/yellow] {fighters_without_images} fighters have no images "
            f"(run: make scrape-sherdog-images)"
        )


async def main():
    """Main entry point."""
    console.print("[bold cyan]Updating Fighter Database[/bold cyan]\n")
    await update_fighter_images()


if __name__ == "__main__":
    asyncio.run(main())
