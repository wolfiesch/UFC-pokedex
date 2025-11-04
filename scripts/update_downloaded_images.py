#!/usr/bin/env python
"""Update database with image URLs for downloaded fighter images."""

import asyncio
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import get_session
from backend.db.models import Fighter

# Load environment variables
load_dotenv()

console = Console()


async def update_fighter_images():
    """Update fighters with image paths."""
    # Check for downloaded images
    images_dir = Path("data/images/fighters")

    # Fighter IDs we just downloaded
    fighter_ids = [
        "d1053e55f00e53fe",  # AJ Cunningham
        "009c4420727149ea",  # AJ Dobson
        "725b1abc9a39d873",  # AJ Fletcher
        "0adf1aacda5e26ac",  # AJ Fonseca
        "18e4f61f16f458c6",  # AJ Matthews
        "f3ec0214794a699e",  # AJ McKee
    ]

    updated_count = 0
    skipped_count = 0

    console.print("[bold cyan]Updating Fighter Database with Image URLs[/bold cyan]\n")

    async with get_session() as session:
        session: AsyncSession

        for fighter_id in fighter_ids:
            # Check which file extension exists
            image_path = None
            for ext in ['jpg', 'png', 'gif']:
                file_path = images_dir / f"{fighter_id}.{ext}"
                if file_path.exists():
                    # Store relative path from API root
                    image_path = f"images/fighters/{fighter_id}.{ext}"
                    break

            if not image_path:
                console.print(f"[yellow]⚠[/yellow] No image found for {fighter_id}")
                skipped_count += 1
                continue

            # Update fighter record
            stmt = (
                update(Fighter)
                .where(Fighter.id == fighter_id)
                .values(
                    image_url=image_path,
                    image_scraped_at=datetime.utcnow(),
                )
            )

            await session.execute(stmt)
            updated_count += 1
            console.print(f"[green]✓[/green] Updated {fighter_id} with {image_path}")

        # Commit all updates
        await session.commit()

    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"[green]✓[/green] Updated {updated_count} fighters")

    if skipped_count > 0:
        console.print(f"[yellow]⚠[/yellow] Skipped {skipped_count} fighters (no image found)")


async def main():
    """Main entry point."""
    await update_fighter_images()


if __name__ == "__main__":
    asyncio.run(main())
