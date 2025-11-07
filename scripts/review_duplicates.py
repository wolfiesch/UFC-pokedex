#!/usr/bin/env python
"""Interactive review of duplicate photos with CLI image previews."""

from dotenv import load_dotenv

load_dotenv()

import asyncio
import base64
import os
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()


def display_image_iterm2(image_path: Path, width: int = 40):
    """Display image using iTerm2 inline image protocol."""
    try:
        # Read image file
        with open(image_path, 'rb') as f:
            image_data = f.read()

        # Encode to base64
        encoded = base64.b64encode(image_data).decode('ascii')

        # iTerm2 inline image escape sequence
        # Width is in character cells
        escape_sequence = f"\033]1337;File=inline=1;width={width};preserveAspectRatio=1:{encoded}\a"

        console.print(escape_sequence)
        return True
    except (OSError, ValueError) as e:
        console.print(f"[dim]iTerm2 display error: {e}[/dim]")
        return False


def display_image_kitty(image_path: Path, width: int = 40):
    """Display image using Kitty graphics protocol."""
    try:
        # Use kitty icat if available
        result = subprocess.run(
            ['kitty', '+kitten', 'icat', '--align', 'left', f'--place={width}x{width}@0x0', str(image_path)],
            capture_output=True,
            timeout=2
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired) as e:
        console.print(f"[dim]Kitty display error: {e}[/dim]")
        return False


def display_image_ascii(image_path: Path, width: int = 80):
    """Display image as ASCII art (fallback)."""
    try:
        from PIL import Image

        img = Image.open(image_path)

        # Resize to terminal width
        aspect_ratio = img.height / img.width
        new_width = width
        new_height = int(aspect_ratio * new_width * 0.5)  # 0.5 to account for character aspect ratio

        img = img.resize((new_width, new_height))
        img = img.convert('L')  # Convert to grayscale

        # ASCII characters from dark to light
        ascii_chars = '@%#*+=-:. '

        # Convert to ASCII
        pixels = list(img.getdata())
        ascii_str = ''
        for i, pixel in enumerate(pixels):
            ascii_str += ascii_chars[pixel // 32]
            if (i + 1) % new_width == 0:
                ascii_str += '\n'

        console.print(ascii_str)
        return True
    except (OSError, ValueError) as e:
        console.print(f"[dim]ASCII display error: {e}[/dim]")
        return False


def display_image(image_path: Path, method: str = 'auto', width: int = 40) -> bool:
    """
    Display image in terminal using best available method.

    Args:
        image_path: Path to image file
        method: 'auto', 'iterm2', 'kitty', 'ascii', or 'open'
        width: Width in characters for display

    Returns:
        True if image was displayed
    """
    if not image_path.exists():
        console.print(f"[red]Image not found: {image_path}[/red]")
        return False

    if method == 'auto':
        # Detect terminal type
        term_program = os.environ.get('TERM_PROGRAM', '')

        if 'iTerm' in term_program:
            method = 'iterm2'
        elif 'kitty' in os.environ.get('TERM', ''):
            method = 'kitty'
        else:
            # Check if we're on macOS and can use qlmanage
            if sys.platform == 'darwin':
                method = 'open'
            else:
                method = 'ascii'

    # Try selected method
    if method == 'iterm2':
        if display_image_iterm2(image_path, width):
            return True
    elif method == 'kitty':
        if display_image_kitty(image_path, width):
            return True
    elif method == 'ascii':
        return display_image_ascii(image_path, width)
    elif method == 'open':
        # Open in system viewer (fallback)
        try:
            if sys.platform == 'darwin':
                subprocess.run(['open', str(image_path)], check=True)
            else:
                subprocess.run(['xdg-open', str(image_path)], check=True)
            return True
        except (OSError, subprocess.CalledProcessError) as e:
            console.print(f"[dim]System viewer error: {e}[/dim]")

    # Final fallback - just show path
    console.print(f"[dim]Image path: {image_path}[/dim]")
    return False


async def get_fighter_info(fighter_ids: list[str]) -> dict:
    """Get fighter information from database."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from backend.db.connection import get_session
    from backend.db.models import Fighter

    async with get_session() as session:
        session: AsyncSession

        stmt = select(Fighter).where(Fighter.id.in_(fighter_ids))
        result = await session.execute(stmt)

        fighters = {f.id: f for f in result.scalars().all()}
        return fighters


async def review_exact_duplicates(duplicates_file: Path, images_dir: Path, display_method: str = 'auto'):
    """Interactively review exact duplicate photos."""

    console.print("[bold cyan]Interactive Duplicate Photo Review[/bold cyan]\n")

    # Load duplicates
    if not duplicates_file.exists():
        console.print(f"[red]Duplicates file not found: {duplicates_file}[/red]")
        console.print("[yellow]Run: make detect-duplicate-photos first[/yellow]")
        return

    # Parse duplicates file
    duplicate_groups = []
    current_group = []

    with open(duplicates_file) as f:
        for line in f:
            line = line.strip()
            if line.startswith('Hash:'):
                if current_group:
                    duplicate_groups.append(current_group)
                current_group = []
            elif line and '\t' in line:
                fighter_id, fighter_name = line.split('\t', 1)
                fighter_id = fighter_id.strip()
                fighter_name = fighter_name.strip()
                current_group.append((fighter_id, fighter_name))

        if current_group:
            duplicate_groups.append(current_group)

    console.print(f"Found {len(duplicate_groups)} groups of exact duplicates\n")

    # Get fighter info
    all_ids = [fid for group in duplicate_groups for fid, _ in group]
    fighters = await get_fighter_info(all_ids)

    # Track images to delete
    images_to_delete = []

    # Review each group
    for idx, group in enumerate(duplicate_groups, 1):
        console.print(f"\n[bold]Duplicate Group {idx}/{len(duplicate_groups)}[/bold]")
        console.print("=" * 80)

        # Display fighter info
        table = Table()
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Fighter Name", style="yellow")
        table.add_column("Record", style="dim")
        table.add_column("Division", style="dim")

        for i, (fighter_id, fighter_name) in enumerate(group, 1):
            fighter = fighters.get(fighter_id)
            record = fighter.record if fighter else "Unknown"
            division = fighter.division if fighter else "Unknown"
            table.add_row(str(i), fighter_name, record or "", division or "")

        console.print(table)
        console.print()

        # Display images
        console.print("[bold]Image Preview:[/bold]\n")

        for i, (fighter_id, fighter_name) in enumerate(group, 1):
            console.print(f"[cyan]Fighter {i}: {fighter_name}[/cyan]")

            # Find image file
            image_path = None
            for ext in ['jpg', 'jpeg', 'png', 'gif']:
                path = images_dir / f"{fighter_id}.{ext}"
                if path.exists():
                    image_path = path
                    break

            if image_path:
                display_image(image_path, method=display_method, width=60)
                console.print(f"[dim]Path: {image_path}[/dim]")
            else:
                console.print("[red]Image file not found[/red]")

            console.print()

        # Prompt for action
        console.print("\n[bold]What would you like to do?[/bold]")
        console.print(f"  1-{len(group)}: Keep this fighter's image (delete others)")
        console.print("  a: Keep all (skip this group)")
        console.print("  d: Delete all images (will need to re-scrape)")
        console.print("  o: Open all images in system viewer")
        console.print("  s: Skip to next group")
        console.print("  q: Quit review")

        choice = Prompt.ask("\nYour choice", default="s")

        if choice == 'q':
            break
        elif choice == 's' or choice == 'a':
            continue
        elif choice == 'o':
            # Open all images
            for fighter_id, _ in group:
                for ext in ['jpg', 'jpeg', 'png', 'gif']:
                    path = images_dir / f"{fighter_id}.{ext}"
                    if path.exists():
                        if sys.platform == 'darwin':
                            subprocess.run(['open', str(path)])
                        else:
                            subprocess.run(['xdg-open', str(path)])
                        break
            # Ask again
            console.print("\n[yellow]After reviewing, what would you like to do?[/yellow]")
            choice = Prompt.ask("Your choice", default="s")

        if choice == 'd':
            # Delete all
            for fighter_id, fighter_name in group:
                images_to_delete.append((fighter_id, fighter_name))
        elif choice.isdigit():
            # Keep selected fighter, delete others
            keep_idx = int(choice) - 1
            if 0 <= keep_idx < len(group):
                for i, (fighter_id, fighter_name) in enumerate(group):
                    if i != keep_idx:
                        images_to_delete.append((fighter_id, fighter_name))
            else:
                console.print("[red]Invalid choice[/red]")

    # Summary
    if images_to_delete:
        console.print(f"\n[bold yellow]Images marked for deletion: {len(images_to_delete)}[/bold yellow]\n")

        table = Table()
        table.add_column("Fighter ID", style="dim")
        table.add_column("Fighter Name", style="cyan")

        for fighter_id, fighter_name in images_to_delete[:20]:
            table.add_row(fighter_id, fighter_name)

        if len(images_to_delete) > 20:
            table.add_row("...", f"and {len(images_to_delete) - 20} more")

        console.print(table)

        # Save to file
        output_file = Path("data/duplicates_to_delete.txt")
        with open(output_file, "w") as f:
            for fighter_id, fighter_name in images_to_delete:
                f.write(f"{fighter_id}\t{fighter_name}\n")

        console.print(f"\n[green]✓ Saved deletion list to: {output_file}[/green]")

        # Offer to delete now
        if Confirm.ask("\nDelete these images now?"):
            deleted_count = 0
            for fighter_id, fighter_name in images_to_delete:
                for ext in ['jpg', 'jpeg', 'png', 'gif']:
                    path = images_dir / f"{fighter_id}.{ext}"
                    if path.exists():
                        path.unlink()
                        deleted_count += 1
                        console.print(f"[red]Deleted:[/red] {fighter_name} ({path.name})")

            console.print(f"\n[green]✓ Deleted {deleted_count} image files[/green]")
            console.print("\n[bold]Next steps:[/bold]")
            console.print("  1. Sync database: [cyan]make sync-images-to-db[/cyan]")
            console.print("  2. Re-scrape missing: [cyan]make replace-placeholders[/cyan]")
    else:
        console.print("\n[green]No images marked for deletion[/green]")


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Interactive review of duplicate photos with CLI previews"
    )
    parser.add_argument(
        "--method",
        choices=['auto', 'iterm2', 'kitty', 'ascii', 'open'],
        default='auto',
        help="Image display method (default: auto-detect)",
    )

    args = parser.parse_args()

    duplicates_file = Path("data/exact_duplicate_photos.txt")
    images_dir = Path("data/images/fighters")

    await review_exact_duplicates(duplicates_file, images_dir, display_method=args.method)


if __name__ == "__main__":
    asyncio.run(main())
