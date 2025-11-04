#!/usr/bin/env python
"""Find images on disk that aren't in database."""

import asyncio
from pathlib import Path
from rich.console import Console
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

console = Console()


async def main():
    from backend.db.connection import get_session
    from backend.db.models import Fighter

    # Get all fighter IDs from database
    async with get_session() as session:
        session: AsyncSession
        stmt = select(Fighter.id, Fighter.image_url)
        result = await session.execute(stmt)
        db_fighters = {row[0]: row[1] for row in result.all()}

    console.print(f"Database: {len(db_fighters)} fighters")

    # Get all image files
    images_dir = Path("data/images/fighters")
    image_files = set()
    for ext in ['jpg', 'png', 'gif']:
        for img in images_dir.glob(f"*.{ext}"):
            image_files.add(img.stem)

    console.print(f"Disk: {len(image_files)} image files\n")

    # Find unsynced
    console.print("[bold]Images on disk but not in database:[/bold]")
    for fighter_id in image_files:
        if fighter_id not in db_fighters:
            console.print(f"  [yellow]⚠[/yellow] {fighter_id} - NOT IN DATABASE")
        elif db_fighters[fighter_id] is None:
            console.print(f"  [green]✓[/green] {fighter_id} - in DB but NULL image_url")


if __name__ == "__main__":
    asyncio.run(main())
