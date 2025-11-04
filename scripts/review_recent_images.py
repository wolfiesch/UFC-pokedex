#!/usr/bin/env python
"""List recently downloaded images for manual review."""

from dotenv import load_dotenv
load_dotenv()

import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

console = Console()


async def list_recent_images(hours: int = 24) -> None:
    """List fighters with images downloaded in the last N hours."""
    from backend.db.connection import get_session
    from backend.db.models import Fighter

    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    async with get_session() as session:
        session: AsyncSession

        stmt = (
            select(Fighter.id, Fighter.name, Fighter.image_url, Fighter.image_scraped_at)
            .where(Fighter.image_scraped_at >= cutoff_time)
            .order_by(Fighter.image_scraped_at.desc())
        )

        result = await session.execute(stmt)
        fighters = result.all()

    if not fighters:
        console.print(f"[yellow]No images downloaded in the last {hours} hours.[/yellow]")
        return

    # Create table
    table = Table(title=f"Images Downloaded in Last {hours} Hours")
    table.add_column("Name", style="cyan")
    table.add_column("Fighter ID", style="dim")
    table.add_column("Image Path", style="green")
    table.add_column("Downloaded", style="dim")

    images_dir = Path("data/images/fighters")

    for fighter in fighters:
        # Get image file path
        image_file = None
        if fighter.image_url:
            image_filename = Path(fighter.image_url).name
            image_file = images_dir / image_filename

        # Check if file exists
        file_status = "✓" if image_file and image_file.exists() else "✗ MISSING"

        table.add_row(
            fighter.name,
            fighter.id,
            f"{file_status} {fighter.image_url or 'N/A'}",
            fighter.image_scraped_at.strftime("%H:%M:%S") if fighter.image_scraped_at else "N/A"
        )

    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {len(fighters)} images")

    # Print command to open images directory
    console.print(f"\n[dim]To review images:[/dim]")
    console.print(f"  [cyan]open {images_dir}[/cyan]")
    console.print(f"\n[dim]To remove bad images:[/dim]")
    console.print(f"  1. Note the Fighter IDs of bad images")
    console.print(f"  2. Edit [cyan]scripts/remove_bad_images.py[/cyan]")
    console.print(f"  3. Run: [cyan]PYTHONPATH=. .venv/bin/python scripts/remove_bad_images.py[/cyan]")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="List recently downloaded fighter images")
    parser.add_argument("--hours", type=int, default=24, help="Hours to look back (default: 24)")

    args = parser.parse_args()

    console.print("[bold cyan]Recent Fighter Images Review[/bold cyan]\n")
    await list_recent_images(hours=args.hours)


if __name__ == "__main__":
    asyncio.run(main())
