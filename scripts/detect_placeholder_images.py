#!/usr/bin/env python
"""Detect Sherdog placeholder images using perceptual hashing."""

from dotenv import load_dotenv

load_dotenv()

import argparse
from pathlib import Path

import imagehash
from PIL import Image
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


def compute_image_hash(image_path: Path) -> str:
    """Compute perceptual hash of an image."""
    try:
        img = Image.open(image_path)
        # Use average hash - works well for placeholder detection
        return str(imagehash.average_hash(img))
    except (OSError, ValueError) as e:
        console.print(f"[red]Error hashing {image_path.name}: {e}[/red]")
        return None


def find_duplicate_images(images_dir: Path) -> dict[str, dict[str, str]]:
    """Find duplicate images by perceptual hash."""
    console.print("[bold cyan]Detecting Duplicate/Placeholder Images[/bold cyan]\n")

    # Get all image files
    image_files = []
    for ext in ['jpg', 'jpeg', 'png', 'gif']:
        image_files.extend(images_dir.glob(f"*.{ext}"))

    console.print(f"Scanning {len(image_files)} images...\n")

    # Compute hashes
    hash_to_fighters = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Computing image hashes...", total=len(image_files))

        for img_path in image_files:
            img_hash = compute_image_hash(img_path)
            if img_hash:
                fighter_id = img_path.stem
                if img_hash not in hash_to_fighters:
                    hash_to_fighters[img_hash] = {}
                hash_to_fighters[img_hash][fighter_id] = str(img_path)

            progress.advance(task)

    return hash_to_fighters


def analyze_duplicates(hash_to_fighters: dict[str, dict[str, str]]) -> list[tuple[str, dict[str, str]]]:
    """Analyze and display duplicate images."""

    # Find hashes with multiple fighters (duplicates)
    duplicates = {h: fighters for h, fighters in hash_to_fighters.items() if len(fighters) > 1}

    if not duplicates:
        console.print("[green]✓ No duplicate images found![/green]")
        return []

    # Sort by number of duplicates (most common first)
    sorted_dupes = sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)

    console.print(f"\n[yellow]Found {len(duplicates)} unique duplicate images[/yellow]")
    console.print(f"[yellow]Total fighters with duplicates: {sum(len(f) for f in duplicates.values())}[/yellow]\n")

    # Display top duplicates
    console.print("[bold]Top Duplicate Images (likely placeholders):[/bold]\n")

    table = Table()
    table.add_column("Rank", style="dim")
    table.add_column("# Fighters", style="cyan", justify="right")
    table.add_column("Image Hash", style="dim")
    table.add_column("Sample Fighter ID", style="yellow")
    table.add_column("File Path", style="dim")

    for idx, (img_hash, fighters) in enumerate(sorted_dupes[:20], 1):
        # Get first fighter as sample
        first_fighter_id = list(fighters.keys())[0]
        first_path = fighters[first_fighter_id]

        table.add_row(
            str(idx),
            str(len(fighters)),
            img_hash[:16] + "...",
            first_fighter_id,
            Path(first_path).name,
        )

    console.print(table)

    # Most common is likely the Sherdog placeholder
    if sorted_dupes:
        top_hash, top_fighters = sorted_dupes[0]
        console.print(f"\n[bold yellow]⚠ Most common duplicate ({len(top_fighters)} fighters):[/bold yellow]")
        console.print(f"  Hash: {top_hash}")
        console.print(f"  Sample: {list(top_fighters.values())[0]}")
        console.print("\n[dim]This is likely the Sherdog placeholder image[/dim]")

        # Save fighter IDs to file
        output_file = Path("data/placeholder_fighter_ids.txt")
        with open(output_file, "w") as f:
            for fighter_id in top_fighters.keys():
                f.write(f"{fighter_id}\n")

        console.print(f"\n[green]✓ Saved {len(top_fighters)} fighter IDs to: {output_file}[/green]")

    return sorted_dupes


def display_all_duplicates(sorted_dupes: list[tuple[str, dict[str, str]]], limit: int = 10):
    """Display detailed list of all duplicate groups."""
    console.print(f"\n[bold]All Duplicate Groups (showing top {limit}):[/bold]\n")

    for idx, (img_hash, fighters) in enumerate(sorted_dupes[:limit], 1):
        console.print(f"\n[cyan]#{idx} - {len(fighters)} fighters with hash {img_hash[:16]}...[/cyan]")

        # Show up to 10 fighters per group
        for fighter_id in list(fighters.keys())[:10]:
            console.print(f"  {fighter_id}")

        if len(fighters) > 10:
            console.print(f"  [dim]... and {len(fighters) - 10} more[/dim]")


async def get_fighter_names(fighter_ids: list[str]) -> dict[str, str]:
    """Get fighter names from database."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from backend.db.connection import get_session
    from backend.db.models import Fighter

    async with get_session() as session:
        session: AsyncSession

        stmt = select(Fighter.id, Fighter.name).where(Fighter.id.in_(fighter_ids))
        result = await session.execute(stmt)

        return {row.id: row.name for row in result.all()}


async def main():
    parser = argparse.ArgumentParser(
        description="Detect Sherdog placeholder images using perceptual hashing"
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Show all duplicate groups (not just top)",
    )
    parser.add_argument(
        "--with-names",
        action="store_true",
        help="Include fighter names (requires database query)",
    )

    args = parser.parse_args()

    images_dir = Path("data/images/fighters")

    if not images_dir.exists():
        console.print(f"[red]Images directory not found: {images_dir}[/red]")
        return

    # Find duplicates
    hash_to_fighters = find_duplicate_images(images_dir)

    # Analyze and display
    sorted_dupes = analyze_duplicates(hash_to_fighters)

    if args.show_all and sorted_dupes:
        display_all_duplicates(sorted_dupes, limit=50)

    # Show fighter names if requested
    if args.with_names and sorted_dupes:
        top_hash, top_fighters = sorted_dupes[0]
        console.print("\n[bold]Fetching fighter names for placeholder images...[/bold]")

        names = await get_fighter_names(list(top_fighters.keys()))

        console.print("\n[yellow]Fighters with placeholder image:[/yellow]")
        table = Table()
        table.add_column("Fighter ID", style="dim")
        table.add_column("Fighter Name", style="cyan")

        for fighter_id in list(top_fighters.keys())[:50]:
            name = names.get(fighter_id, "Unknown")
            table.add_row(fighter_id, name)

        if len(top_fighters) > 50:
            table.add_row("...", f"and {len(top_fighters) - 50} more")

        console.print(table)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
