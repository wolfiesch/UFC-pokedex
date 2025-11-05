#!/usr/bin/env python
"""Sync image files on disk to database (both additions and deletions)."""

from dotenv import load_dotenv

load_dotenv()

import asyncio
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

console = Console()


async def sync_images():
    """Sync filesystem image state to database (additions + deletions)."""
    from backend.db.connection import get_session
    from backend.db.models import Fighter

    console.print("[bold cyan]Syncing Images to Database[/bold cyan]\n")

    images_dir = Path("data/images/fighters")

    # Get all image files on disk
    image_files = {}
    for ext in ['jpg', 'jpeg', 'png', 'gif']:
        for img_file in images_dir.glob(f"*.{ext}"):
            fighter_id = img_file.stem
            image_files[fighter_id] = f"images/fighters/{img_file.name}"

    console.print(f"Found {len(image_files)} image files on disk\n")

    async with get_session() as session:
        session: AsyncSession

        # === STEP 1: Remove image_url for deleted files ===
        stmt = select(Fighter.id, Fighter.name, Fighter.image_url).where(
            Fighter.image_url.isnot(None)
        )
        result = await session.execute(stmt)
        fighters_with_urls = result.all()

        console.print(f"Checking {len(fighters_with_urls)} fighters with image_url...")

        deleted_count = 0
        deleted_fighters = []

        for fighter in fighters_with_urls:
            fighter_id = fighter.id
            if fighter_id not in image_files:
                # Image was deleted - reset database
                stmt = (
                    update(Fighter)
                    .where(Fighter.id == fighter_id)
                    .values(image_url=None, image_scraped_at=None)
                )
                await session.execute(stmt)
                deleted_count += 1
                deleted_fighters.append((fighter_id, fighter.name))

        if deleted_count > 0:
            console.print(f"\n[yellow]Reset {deleted_count} fighters with deleted images:[/yellow]")
            table = Table()
            table.add_column("Fighter Name", style="cyan")
            table.add_column("Fighter ID", style="dim")

            for fighter_id, name in deleted_fighters[:20]:
                table.add_row(name, fighter_id)

            if len(deleted_fighters) > 20:
                table.add_row("...", f"and {len(deleted_fighters) - 20} more")

            console.print(table)
        else:
            console.print("[green]✓ No deleted images found[/green]")

        # === STEP 2: Add image_url for new files ===
        console.print("\n[bold]Adding image URLs for new files...[/bold]")

        added_count = 0
        added_fighters = []

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
                # Get fighter name for display
                stmt_name = select(Fighter.name).where(Fighter.id == fighter_id)
                name_result = await session.execute(stmt_name)
                name = name_result.scalar_one_or_none()

                added_count += 1
                added_fighters.append((fighter_id, name or "Unknown"))

        if added_count > 0:
            console.print(f"\n[green]Added {added_count} new image URLs:[/green]")
            table = Table()
            table.add_column("Fighter Name", style="cyan")
            table.add_column("Fighter ID", style="dim")

            for fighter_id, name in added_fighters[:20]:
                table.add_row(name, fighter_id)

            if len(added_fighters) > 20:
                table.add_row("...", f"and {len(added_fighters) - 20} more")

            console.print(table)
        else:
            console.print("[green]✓ No new images to add[/green]")

        await session.commit()

    # === SUMMARY ===
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Images on disk: {len(image_files)}")
    console.print(f"  Deleted from DB: {deleted_count}")
    console.print(f"  Added to DB: {added_count}")
    console.print("  [green]✓ Database is now in sync with filesystem[/green]")


if __name__ == "__main__":
    asyncio.run(sync_images())
