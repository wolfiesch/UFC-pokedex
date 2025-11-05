#!/usr/bin/env python
"""Replace Sherdog placeholder images with real images from Bing."""

from dotenv import load_dotenv

load_dotenv()

import argparse
import asyncio
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

console = Console()


async def get_fighters_by_ids(fighter_ids: list[str]) -> list[dict]:
    """Get fighter details from database."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from backend.db.connection import get_session
    from backend.db.models import Fighter

    async with get_session() as session:
        session: AsyncSession

        stmt = select(Fighter.id, Fighter.name).where(Fighter.id.in_(fighter_ids))
        result = await session.execute(stmt)

        return [{"id": row.id, "name": row.name} for row in result.all()]


async def main():
    parser = argparse.ArgumentParser(
        description="Replace Sherdog placeholder images with real images from Bing"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of fighters to process (default: 50)",
    )
    parser.add_argument(
        "--skip-tapology",
        action="store_true",
        help="Skip Tapology and go straight to Bing",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without downloading",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    console.print("[bold cyan]Replace Sherdog Placeholder Images[/bold cyan]\n")

    # Read fighter IDs from file
    placeholder_file = Path("data/placeholder_fighter_ids.txt")

    if not placeholder_file.exists():
        console.print(f"[red]Placeholder IDs file not found: {placeholder_file}[/red]")
        console.print("[yellow]Run: PYTHONPATH=. .venv/bin/python scripts/detect_placeholder_images.py first[/yellow]")
        return

    fighter_ids = []
    with open(placeholder_file) as f:
        fighter_ids = [line.strip() for line in f if line.strip()]

    console.print(f"Found {len(fighter_ids)} fighters with placeholder images")

    # Limit batch size
    fighter_ids = fighter_ids[:args.batch_size]
    console.print(f"Processing batch of {len(fighter_ids)} fighters\n")

    # Get fighter details from database
    console.print("Fetching fighter names from database...")
    fighters = await get_fighters_by_ids(fighter_ids)

    if not fighters:
        console.print("[red]No fighters found in database[/red]")
        return

    console.print(f"Found {len(fighters)} fighters in database\n")

    if args.dry_run:
        console.print("[yellow]DRY RUN - Showing fighters to process:[/yellow]\n")
        for fighter in fighters[:20]:
            console.print(f"  {fighter['id']}: {fighter['name']}")
        if len(fighters) > 20:
            console.print(f"  ... and {len(fighters) - 20} more")
        return

    # Confirm before proceeding
    console.print("[bold]Sources that will be used:[/bold]")
    if not args.skip_tapology:
        console.print("  1. Tapology (MMA database)")
    console.print(f"  {'2' if not args.skip_tapology else '1'}. Bing Images (search engine)")
    console.print("\n[dim]Note: Skipping Wikimedia Commons and Sherdog (has placeholders)[/dim]\n")

    if not args.yes:
        if not Confirm.ask(f"Replace {len(fighters)} placeholder images?"):
            console.print("[red]Cancelled[/red]")
            return

    # Import and run the orchestrator logic
    from scripts.image_scraper_orchestrator import (
        download_image,
        search_bing_images,
        search_tapology,
        update_database,
    )

    images_dir = Path("data/images/fighters")

    success_count = 0
    failure_count = 0
    sources_used = {}
    successful_fighter_ids = []

    for idx, fighter in enumerate(fighters, 1):
        fighter_id = fighter["id"]
        fighter_name = fighter["name"]

        console.print(f"\n[bold cyan][{idx}/{len(fighters)}] {fighter_name}[/bold cyan]")
        console.print(f"  ID: {fighter_id}")

        # Delete old placeholder first
        for ext in ['jpg', 'jpeg', 'png', 'gif']:
            old_file = images_dir / f"{fighter_id}.{ext}"
            if old_file.exists():
                old_file.unlink()
                console.print("  [dim]Deleted old placeholder[/dim]")

        image_url = None
        source = None

        # Try Tapology first (unless skipped)
        if not args.skip_tapology:
            console.print("  [dim]Trying Tapology...[/dim]")
            image_url = search_tapology(fighter_name)
            if image_url and download_image(image_url, fighter_id, images_dir, "tapology"):
                source = "Tapology"

        # Try Bing Images if Tapology failed
        if not source:
            import time
            time.sleep(1)
            console.print("  [dim]Trying Bing Images...[/dim]")
            image_url = search_bing_images(fighter_name)
            if image_url and download_image(image_url, fighter_id, images_dir, "bing"):
                source = "Bing Images"

        # Update database
        if source:
            db_updated = await update_database(fighter_id, images_dir)
            if db_updated:
                console.print(f"  [green]✓ Downloaded from {source}[/green]")
                success_count += 1
                successful_fighter_ids.append(fighter_id)
                sources_used[source] = sources_used.get(source, 0) + 1
            else:
                console.print("  [red]✗ Downloaded but database update failed[/red]")
                failure_count += 1
        else:
            console.print("  [red]✗ No image found[/red]")
            failure_count += 1

        # Rate limiting
        if idx < len(fighters):
            import time
            time.sleep(3)

    # Summary
    console.print("\n[bold]Replacement Summary:[/bold]")
    console.print(f"  Success: {success_count}/{len(fighters)}")
    console.print(f"  Failed: {failure_count}/{len(fighters)}")

    if sources_used:
        console.print("\n[bold]Sources Used:[/bold]")
        for source, count in sorted(sources_used.items(), key=lambda x: x[1], reverse=True):
            console.print(f"  {source}: {count}")

    # Suggest verification
    if success_count > 0:
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  1. Verify images: [cyan]make verify-replacement[/cyan]")
        console.print("  2. Sync to database: [cyan]make sync-images-to-db[/cyan]")

    # Calculate remaining
    remaining = len(fighter_ids) - len(fighters)
    if remaining > 0:
        console.print(f"\n[yellow]Remaining placeholders: {remaining}[/yellow]")
        console.print("[dim]Run again to process more[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
