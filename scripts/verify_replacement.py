#!/usr/bin/env python
"""Verify recently replaced placeholder images."""

from dotenv import load_dotenv
load_dotenv()

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.table import Table
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

console = Console()


async def verify_recent_replacements(hours: int = 2):
    """Verify images replaced in the last N hours."""
    from backend.db.connection import get_session
    from backend.db.models import Fighter
    from scripts.validate_fighter_images import validate_image

    console.print(f"[bold cyan]Verifying Recently Replaced Images (last {hours} hours)[/bold cyan]\n")

    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    images_dir = Path("data/images/fighters")

    async with get_session() as session:
        session: AsyncSession

        # Get fighters with recently updated images
        stmt = (
            select(Fighter.id, Fighter.name, Fighter.image_url, Fighter.image_scraped_at)
            .where(Fighter.image_scraped_at >= cutoff_time)
            .order_by(Fighter.image_scraped_at.desc())
        )

        result = await session.execute(stmt)
        recent_fighters = result.all()

    if not recent_fighters:
        console.print(f"[yellow]No images updated in the last {hours} hours[/yellow]")
        return

    console.print(f"Found {len(recent_fighters)} recently updated images\n")

    # Validate each image
    valid_count = 0
    invalid_count = 0
    invalid_details = []

    console.print("[bold]Validating images...[/bold]\n")

    for fighter in recent_fighters:
        fighter_id = fighter.id
        fighter_name = fighter.name

        # Find image file
        image_path = None
        for ext in ['jpg', 'jpeg', 'png', 'gif']:
            path = images_dir / f"{fighter_id}.{ext}"
            if path.exists():
                image_path = path
                break

        if not image_path:
            console.print(f"[red]✗ {fighter_name}[/red] - Image file not found")
            invalid_count += 1
            invalid_details.append((fighter_id, fighter_name, ["Image file missing"]))
            continue

        # Validate image
        validation = validate_image(image_path)

        if validation['valid']:
            console.print(f"[green]✓ {fighter_name}[/green]")
            valid_count += 1
        else:
            issues_str = ", ".join(validation['issues'])
            console.print(f"[red]✗ {fighter_name}[/red] - {issues_str}")
            invalid_count += 1
            invalid_details.append((fighter_id, fighter_name, validation['issues']))

    # Summary
    console.print(f"\n[bold]Verification Results:[/bold]")
    console.print(f"  ✓ Valid: {valid_count}/{len(recent_fighters)}")
    console.print(f"  ✗ Invalid: {invalid_count}/{len(recent_fighters)}")

    if invalid_count > 0:
        success_rate = (valid_count / len(recent_fighters)) * 100
        console.print(f"  Success Rate: {success_rate:.1f}%")

        # Show invalid images
        console.print(f"\n[yellow]Invalid Images:[/yellow]\n")

        table = Table()
        table.add_column("Fighter Name", style="cyan")
        table.add_column("Fighter ID", style="dim")
        table.add_column("Issues", style="red")

        for fighter_id, fighter_name, issues in invalid_details:
            table.add_row(fighter_name, fighter_id, ", ".join(issues))

        console.print(table)

        # Save to file
        invalid_file = Path("data/verification_failures.txt")
        with open(invalid_file, "w") as f:
            for fighter_id, fighter_name, issues in invalid_details:
                f.write(f"{fighter_id}\t{fighter_name}\t{', '.join(issues)}\n")

        console.print(f"\n[dim]Failed IDs saved to: {invalid_file}[/dim]")

        # Suggest action
        console.print(f"\n[bold]Recommended Action:[/bold]")
        console.print(f"  1. Review images manually: [cyan]open {images_dir}[/cyan]")
        console.print(f"  2. Delete bad images: Edit and run [cyan]make remove-bad-images[/cyan]")
        console.print(f"  3. Re-run replacement: [cyan]make replace-placeholders[/cyan]")
    else:
        console.print(f"\n[green]✓ All recently replaced images passed validation![/green]")


async def verify_all_non_placeholders():
    """Verify all images that are not placeholders."""
    from backend.db.connection import get_session
    from backend.db.models import Fighter
    from scripts.validate_fighter_images import validate_image
    from scripts.detect_placeholder_images import compute_image_hash

    console.print("[bold cyan]Verifying All Non-Placeholder Images[/bold cyan]\n")

    images_dir = Path("data/images/fighters")

    # Load placeholder hash
    placeholder_ids_file = Path("data/placeholder_fighter_ids.txt")
    placeholder_ids = set()

    if placeholder_ids_file.exists():
        with open(placeholder_ids_file) as f:
            placeholder_ids = {line.strip() for line in f if line.strip()}

    console.print(f"Excluding {len(placeholder_ids)} known placeholders\n")

    async with get_session() as session:
        session: AsyncSession

        # Get all fighters with images
        stmt = select(Fighter.id, Fighter.name, Fighter.image_url).where(
            Fighter.image_url.isnot(None)
        )

        result = await session.execute(stmt)
        all_fighters = result.all()

    # Filter out placeholders
    fighters_to_check = [
        f for f in all_fighters if f.id not in placeholder_ids
    ]

    console.print(f"Validating {len(fighters_to_check)} non-placeholder images...\n")

    valid_count = 0
    invalid_count = 0
    invalid_details = []

    for idx, fighter in enumerate(fighters_to_check, 1):
        if idx % 100 == 0:
            console.print(f"  Progress: {idx}/{len(fighters_to_check)}")

        fighter_id = fighter.id
        fighter_name = fighter.name

        # Find image file
        image_path = None
        for ext in ['jpg', 'jpeg', 'png', 'gif']:
            path = images_dir / f"{fighter_id}.{ext}"
            if path.exists():
                image_path = path
                break

        if not image_path:
            invalid_count += 1
            invalid_details.append((fighter_id, fighter_name, ["Image file missing"]))
            continue

        # Validate image
        validation = validate_image(image_path)

        if validation['valid']:
            valid_count += 1
        else:
            invalid_count += 1
            invalid_details.append((fighter_id, fighter_name, validation['issues']))

    # Summary
    console.print(f"\n[bold]Verification Results:[/bold]")
    console.print(f"  ✓ Valid: {valid_count}/{len(fighters_to_check)}")
    console.print(f"  ✗ Invalid: {invalid_count}/{len(fighters_to_check)}")
    console.print(f"  Success Rate: {(valid_count / len(fighters_to_check) * 100):.1f}%")

    if invalid_count > 0:
        console.print(f"\n[yellow]Showing first 20 invalid images:[/yellow]\n")

        table = Table()
        table.add_column("Fighter Name", style="cyan")
        table.add_column("Fighter ID", style="dim")
        table.add_column("Issues", style="red")

        for fighter_id, fighter_name, issues in invalid_details[:20]:
            table.add_row(fighter_name, fighter_id, ", ".join(issues))

        if len(invalid_details) > 20:
            table.add_row("...", f"and {len(invalid_details) - 20} more", "")

        console.print(table)

        # Save to file
        invalid_file = Path("data/all_validation_failures.txt")
        with open(invalid_file, "w") as f:
            for fighter_id, fighter_name, issues in invalid_details:
                f.write(f"{fighter_id}\t{fighter_name}\t{', '.join(issues)}\n")

        console.print(f"\n[dim]All failed IDs saved to: {invalid_file}[/dim]")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify replaced placeholder images"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=2,
        help="Hours to look back for recent replacements (default: 2)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Verify all non-placeholder images (slow)",
    )

    args = parser.parse_args()

    if args.all:
        asyncio.run(verify_all_non_placeholders())
    else:
        asyncio.run(verify_recent_replacements(hours=args.hours))
