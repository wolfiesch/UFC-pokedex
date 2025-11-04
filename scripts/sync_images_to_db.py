#!/usr/bin/env python
"""Sync image files on disk to database."""

import asyncio
from datetime import datetime
from pathlib import Path

from rich.console import Console
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

console = Console()


async def sync_images():
    """Find image files and update database for fighters missing image_url."""
    from backend.db.connection import get_session
    from backend.db.models import Fighter

    console.print("[bold cyan]Syncing Images to Database[/bold cyan]\n")

    # Get all image files
    images_dir = Path("data/images/fighters")
    image_files = {}

    for ext in ['jpg', 'png', 'gif']:
        for img_file in images_dir.glob(f"*.{ext}"):
            fighter_id = img_file.stem
            image_files[fighter_id] = f"images/fighters/{img_file.name}"

    console.print(f"Found {len(image_files)} image files on disk")

    # Update database
    updated_count = 0

    async with get_session() as session:
        session: AsyncSession

        for fighter_id, image_path in image_files.items():
            # Update if fighter exists and has no image_url
            stmt = (
                update(Fighter)
                .where(Fighter.id == fighter_id)
                .where(Fighter.image_url.is_(None))
                .values(
                    image_url=image_path,
                    image_scraped_at=datetime.utcnow(),
                )
            )

            result = await session.execute(stmt)
            if result.rowcount > 0:
                updated_count += 1
                console.print(f"[green]✓[/green] Updated {fighter_id}")

        await session.commit()

    console.print(f"\n[green]✓[/green] Updated {updated_count} fighters")


if __name__ == "__main__":
    asyncio.run(sync_images())
