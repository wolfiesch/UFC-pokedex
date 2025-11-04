#!/usr/bin/env python
"""Populate image URLs for fighters with existing image files."""

from __future__ import annotations

import asyncio
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import get_session
from backend.db.models import Fighter

# Load environment variables
load_dotenv()

console = Console()


async def populate_image_urls():
    """Populate image_url field for fighters with existing images on disk."""
    # Get all image files
    images_dir = Path("data/images/fighters")
    if not images_dir.exists():
        console.print(f"[red]Error:[/red] Images directory not found: {images_dir}")
        return

    # Build a mapping of fighter_id -> image filename
    image_files = {}
    for img_file in images_dir.glob("*"):
        if img_file.is_file() and img_file.suffix in [".jpg", ".png", ".jpeg"]:
            fighter_id = img_file.stem  # filename without extension
            # Store relative path: images/fighters/{id}.jpg
            image_files[fighter_id] = f"images/fighters/{img_file.name}"

    console.print(f"Found {len(image_files)} image files on disk")

    if not image_files:
        console.print("[yellow]No images found to populate[/yellow]")
        return

    # Update database
    updated_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Updating fighters...", total=len(image_files))

        async with get_session() as session:
            session: AsyncSession

            for fighter_id, image_path in image_files.items():
                # Update fighter record
                stmt = (
                    update(Fighter)
                    .where(Fighter.id == fighter_id)
                    .values(image_url=image_path)
                )

                result = await session.execute(stmt)
                if result.rowcount > 0:
                    updated_count += 1
                progress.advance(task)

            # Commit all updates
            await session.commit()

    console.print(f"\n[green]✓[/green] Updated {updated_count} fighters with image URLs")

    not_found = len(image_files) - updated_count
    if not_found > 0:
        console.print(
            f"[yellow]⚠[/yellow] {not_found} images found on disk but no matching fighter in database"
        )


async def main():
    """Main entry point."""
    console.print("[bold cyan]Populating Fighter Image URLs[/bold cyan]\n")
    await populate_image_urls()


if __name__ == "__main__":
    asyncio.run(main())
