#!/usr/bin/env python
"""Detect duplicate or very similar photos assigned to different fighters."""

from dotenv import load_dotenv

load_dotenv()

import argparse
import asyncio
from collections import defaultdict
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
        # Use average hash for good balance of speed and accuracy
        return str(imagehash.average_hash(img, hash_size=8))
    except Exception:
        return None


def compute_phash(image_path: Path) -> str:
    """Compute perceptual hash (more robust to modifications)."""
    try:
        img = Image.open(image_path)
        return str(imagehash.phash(img, hash_size=8))
    except Exception:
        return None


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


async def find_duplicate_photos(
    images_dir: Path,
    exclude_placeholders: bool = True,
    similarity_threshold: int = 5,
) -> tuple[list[tuple], list[tuple]]:
    """
    Find duplicate and similar photos across different fighters.

    Args:
        images_dir: Directory containing fighter images
        exclude_placeholders: Skip known placeholder images
        similarity_threshold: Hamming distance for near-duplicates (0-64, lower = more similar)

    Returns:
        exact_duplicates: List of (hash, [fighter_ids]) for exact matches
        near_duplicates: List of ((id1, id2, distance)) for similar images
    """
    console.print("[bold cyan]Detecting Duplicate Fighter Photos[/bold cyan]\n")

    # Load placeholder IDs to exclude
    placeholder_ids = set()
    if exclude_placeholders:
        placeholder_file = Path("data/placeholder_fighter_ids.txt")
        if placeholder_file.exists():
            with open(placeholder_file) as f:
                placeholder_ids = {line.strip() for line in f if line.strip()}
            console.print(f"Excluding {len(placeholder_ids)} known placeholders\n")

    # Get all image files
    image_files = []
    for ext in ['jpg', 'jpeg', 'png', 'gif']:
        for img_path in images_dir.glob(f"*.{ext}"):
            fighter_id = img_path.stem
            if fighter_id not in placeholder_ids:
                image_files.append(img_path)

    console.print(f"Scanning {len(image_files)} fighter images...\n")

    # Compute hashes for all images
    hash_to_fighters = defaultdict(list)
    fighter_hashes = {}  # fighter_id -> (hash, path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Computing image hashes...", total=len(image_files))

        for img_path in image_files:
            fighter_id = img_path.stem
            img_hash = compute_image_hash(img_path)

            if img_hash:
                hash_to_fighters[img_hash].append(fighter_id)
                fighter_hashes[fighter_id] = (imagehash.hex_to_hash(img_hash), str(img_path))

            progress.advance(task)

    # Find exact duplicates (same hash)
    exact_duplicates = [
        (hash_str, fighters)
        for hash_str, fighters in hash_to_fighters.items()
        if len(fighters) > 1
    ]

    # Find near-duplicates (similar hash)
    near_duplicates = []
    fighter_ids = list(fighter_hashes.keys())

    if similarity_threshold > 0:
        console.print(f"\nFinding near-duplicates (similarity threshold: {similarity_threshold})...\n")

        # Compare all pairs (only upper triangle to avoid duplicates)
        for i in range(len(fighter_ids)):
            for j in range(i + 1, len(fighter_ids)):
                id1, id2 = fighter_ids[i], fighter_ids[j]
                hash1, _ = fighter_hashes[id1]
                hash2, _ = fighter_hashes[id2]

                # Calculate Hamming distance
                distance = hash1 - hash2

                if 0 < distance <= similarity_threshold:
                    near_duplicates.append((id1, id2, distance))

    return exact_duplicates, near_duplicates


async def display_duplicate_results(
    exact_duplicates: list[tuple],
    near_duplicates: list[tuple],
    show_all: bool = False,
):
    """Display duplicate detection results."""

    # === EXACT DUPLICATES ===
    if exact_duplicates:
        console.print(f"[bold red]Found {len(exact_duplicates)} groups of exact duplicates![/bold red]\n")

        # Sort by number of fighters (most concerning first)
        exact_duplicates.sort(key=lambda x: len(x[1]), reverse=True)

        # Get fighter names
        all_fighter_ids = []
        for _, fighters in exact_duplicates:
            all_fighter_ids.extend(fighters)

        names = await get_fighter_names(all_fighter_ids)

        # Display table
        table = Table(title="Exact Duplicate Photos")
        table.add_column("# Fighters", style="red", justify="right")
        table.add_column("Hash", style="dim")
        table.add_column("Fighter Names", style="cyan")

        display_count = len(exact_duplicates) if show_all else min(20, len(exact_duplicates))

        for hash_str, fighters in exact_duplicates[:display_count]:
            fighter_names = [names.get(fid, fid) for fid in fighters]
            names_str = "\n".join(fighter_names[:5])
            if len(fighter_names) > 5:
                names_str += f"\n... and {len(fighter_names) - 5} more"

            table.add_row(
                str(len(fighters)),
                hash_str[:16] + "...",
                names_str,
            )

        if len(exact_duplicates) > 20 and not show_all:
            table.add_row("...", f"and {len(exact_duplicates) - 20} more groups", "")

        console.print(table)

        # Save to file
        output_file = Path("data/exact_duplicate_photos.txt")
        with open(output_file, "w") as f:
            for hash_str, fighters in exact_duplicates:
                f.write(f"Hash: {hash_str}\n")
                for fid in fighters:
                    name = names.get(fid, fid)
                    f.write(f"  {fid}\t{name}\n")
                f.write("\n")

        console.print(f"\n[green]✓ Saved exact duplicates to: {output_file}[/green]")

    else:
        console.print("[green]✓ No exact duplicate photos found![/green]\n")

    # === NEAR DUPLICATES ===
    if near_duplicates:
        console.print(f"\n[yellow]Found {len(near_duplicates)} pairs of similar photos[/yellow]\n")

        # Sort by similarity (lowest distance first)
        near_duplicates.sort(key=lambda x: x[2])

        # Get fighter names
        all_ids = set()
        for id1, id2, _ in near_duplicates:
            all_ids.add(id1)
            all_ids.add(id2)

        names = await get_fighter_names(list(all_ids))

        # Display table
        table = Table(title="Similar Photos (Near-Duplicates)")
        table.add_column("Similarity", style="yellow", justify="right")
        table.add_column("Fighter 1", style="cyan")
        table.add_column("Fighter 2", style="cyan")

        display_count = len(near_duplicates) if show_all else min(20, len(near_duplicates))

        for id1, id2, distance in near_duplicates[:display_count]:
            similarity_pct = 100 * (1 - distance / 64)
            name1 = names.get(id1, id1)
            name2 = names.get(id2, id2)

            table.add_row(
                f"{similarity_pct:.1f}%",
                f"{name1} ({id1[:8]}...)",
                f"{name2} ({id2[:8]}...)",
            )

        if len(near_duplicates) > 20 and not show_all:
            table.add_row("...", f"and {len(near_duplicates) - 20} more pairs", "")

        console.print(table)

        # Save to file
        output_file = Path("data/similar_photos.txt")
        with open(output_file, "w") as f:
            for id1, id2, distance in near_duplicates:
                similarity = 100 * (1 - distance / 64)
                name1 = names.get(id1, id1)
                name2 = names.get(id2, id2)
                f.write(f"Similarity: {similarity:.1f}% (distance: {distance})\n")
                f.write(f"  {id1}\t{name1}\n")
                f.write(f"  {id2}\t{name2}\n")
                f.write("\n")

        console.print(f"\n[green]✓ Saved similar photos to: {output_file}[/green]")

    else:
        console.print("[green]✓ No similar photos found![/green]\n")

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  Exact duplicates: {len(exact_duplicates)} groups")
    console.print(f"  Near-duplicates: {len(near_duplicates)} pairs")

    if exact_duplicates or near_duplicates:
        console.print("\n[bold]Recommended Action:[/bold]")
        console.print("  1. Review duplicate images manually")
        console.print("  2. Delete incorrect images using [cyan]make remove-bad-images[/cyan]")
        console.print("  3. Re-run scraper for affected fighters")


async def main():
    parser = argparse.ArgumentParser(
        description="Detect duplicate or very similar photos across different fighters"
    )
    parser.add_argument(
        "--include-placeholders",
        action="store_true",
        help="Include known placeholder images in search",
    )
    parser.add_argument(
        "--similarity",
        type=int,
        default=5,
        help="Similarity threshold (0-64, lower = stricter). Default: 5",
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Show all duplicates (not just first 20)",
    )
    parser.add_argument(
        "--exact-only",
        action="store_true",
        help="Only find exact duplicates (faster)",
    )

    args = parser.parse_args()

    images_dir = Path("data/images/fighters")

    if not images_dir.exists():
        console.print(f"[red]Images directory not found: {images_dir}[/red]")
        return

    # Find duplicates
    exact_duplicates, near_duplicates = await find_duplicate_photos(
        images_dir,
        exclude_placeholders=not args.include_placeholders,
        similarity_threshold=0 if args.exact_only else args.similarity,
    )

    # Display results
    await display_duplicate_results(
        exact_duplicates,
        near_duplicates,
        show_all=args.show_all,
    )


if __name__ == "__main__":
    asyncio.run(main())
