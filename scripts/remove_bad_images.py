#!/usr/bin/env python
"""Remove bad fighter images and reset database entries."""

from dotenv import load_dotenv
load_dotenv()

import asyncio
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

console = Console()


async def remove_bad_images(fighter_ids: list[str]) -> None:
    """Remove image files and reset database entries for specified fighters."""
    from backend.db.connection import get_session
    from backend.db.models import Fighter

    images_dir = Path("data/images/fighters")

    console.print(f"\n[bold yellow]Removing images for {len(fighter_ids)} fighters[/bold yellow]")

    removed_files = 0
    updated_db = 0

    # Remove image files
    for fighter_id in fighter_ids:
        for ext in ['jpg', 'png', 'gif']:
            image_path = images_dir / f"{fighter_id}.{ext}"
            if image_path.exists():
                console.print(f"  [red]Deleting:[/red] {image_path.name}")
                image_path.unlink()
                removed_files += 1

    # Update database to set image_url = NULL
    async with get_session() as session:
        session: AsyncSession

        for fighter_id in fighter_ids:
            stmt = (
                update(Fighter)
                .where(Fighter.id == fighter_id)
                .values(image_url=None, image_scraped_at=None)
            )
            await session.execute(stmt)
            updated_db += 1

        await session.commit()

    console.print(f"\n[bold green]✓ Complete![/bold green]")
    console.print(f"  Files removed: {removed_files}")
    console.print(f"  Database entries reset: {updated_db}")
    console.print(f"\n[dim]You can now re-run the orchestrator to get better images for these fighters.[/dim]")


async def main():
    """Main entry point."""
    console.print("[bold cyan]Remove Bad Fighter Images[/bold cyan]\n")

    # Instructions
    console.print("[bold]Instructions:[/bold]")
    console.print("1. Edit the FIGHTER_IDS list below with the IDs of fighters with bad images")
    console.print("2. Run this script: [cyan]PYTHONPATH=. .venv/bin/python scripts/remove_bad_images.py[/cyan]")
    console.print("3. Re-run orchestrator: [cyan]make scrape-images-orchestrator[/cyan]\n")

    # List of fighter IDs with bad images
    # EDIT THIS LIST - Add fighter IDs you want to remove
    FIGHTER_IDS = [
        # Example: "f689bd7bbd14b392",  # Cyborg Abreu (bad image)
        # Example: "6fd953151d981979",  # JJ Aldrich (wrong person)
        # Add your fighter IDs here
    ]

    if not FIGHTER_IDS:
        console.print("[yellow]⚠ No fighter IDs specified. Edit FIGHTER_IDS in the script.[/yellow]")
        console.print("\n[dim]To find fighter IDs:[/dim]")
        console.print("  1. Check image files: ls data/images/fighters/")
        console.print("  2. Database query: SELECT id, name FROM fighters WHERE image_url IS NOT NULL;")
        return

    # Confirm before proceeding
    console.print(f"[bold]Fighters to remove:[/bold] {len(FIGHTER_IDS)}")
    for fid in FIGHTER_IDS[:5]:
        console.print(f"  - {fid}")
    if len(FIGHTER_IDS) > 5:
        console.print(f"  ... and {len(FIGHTER_IDS) - 5} more")

    if not Confirm.ask("\n[bold yellow]Proceed with removal?[/bold yellow]"):
        console.print("[red]Cancelled.[/red]")
        return

    await remove_bad_images(FIGHTER_IDS)


if __name__ == "__main__":
    asyncio.run(main())
