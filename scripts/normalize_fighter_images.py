#!/usr/bin/env python
"""Normalize fighter images to consistent size and format."""

import argparse
from pathlib import Path

from PIL import Image
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

console = Console()


def normalize_image(
    input_path: Path,
    output_path: Path,
    target_size: tuple[int, int] = (300, 300),
    quality: int = 85,
    dry_run: bool = False,
) -> dict:
    """
    Normalize an image to target size with smart cropping.

    Args:
        input_path: Source image path
        output_path: Destination image path
        target_size: Target (width, height) in pixels
        quality: JPEG quality (1-100)
        dry_run: If True, only analyze without saving

    Returns:
        dict with status, original_size, new_size, file_size_before, file_size_after
    """
    try:
        # Open image
        img = Image.open(input_path)
        original_size = img.size
        original_file_size = input_path.stat().st_size

        # Convert to RGB if needed (handles transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background

        # Calculate crop dimensions for center crop
        # This preserves the center of the image
        width, height = img.size
        aspect_ratio = width / height
        target_aspect = target_size[0] / target_size[1]

        if aspect_ratio > target_aspect:
            # Image is wider - crop sides
            new_width = int(height * target_aspect)
            left = (width - new_width) // 2
            img = img.crop((left, 0, left + new_width, height))
        elif aspect_ratio < target_aspect:
            # Image is taller - crop top/bottom
            new_height = int(width / target_aspect)
            top = (height - new_height) // 2
            img = img.crop((0, top, width, top + new_height))

        # Resize to target size
        img = img.resize(target_size, Image.Resampling.LANCZOS)

        if not dry_run:
            # Save as JPEG
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, 'JPEG', quality=quality, optimize=True)
            new_file_size = output_path.stat().st_size
        else:
            new_file_size = None

        return {
            'status': 'success',
            'original_size': original_size,
            'new_size': target_size,
            'file_size_before': original_file_size,
            'file_size_after': new_file_size,
        }

    except (OSError, ValueError) as e:
        return {
            'status': 'error',
            'error': str(e),
        }


def normalize_all_images(
    images_dir: Path,
    target_size: tuple[int, int] = (300, 300),
    quality: int = 85,
    dry_run: bool = False,
    backup: bool = True,
) -> None:
    """
    Normalize all fighter images in directory.

    Args:
        images_dir: Directory containing fighter images
        target_size: Target (width, height) in pixels
        quality: JPEG quality (1-100)
        dry_run: If True, only analyze without saving
        backup: If True, backup original images before normalizing
    """
    console.print("[bold cyan]Fighter Image Normalization[/bold cyan]\n")

    # Find all image files
    image_files = []
    for ext in ['jpg', 'jpeg', 'png', 'gif']:
        image_files.extend(images_dir.glob(f"*.{ext}"))

    if not image_files:
        console.print("[yellow]No images found to normalize[/yellow]")
        return

    console.print(f"Found {len(image_files)} images to normalize")
    console.print(f"Target size: {target_size[0]}x{target_size[1]} pixels")
    console.print(f"JPEG quality: {quality}")

    if dry_run:
        console.print("[yellow]DRY RUN - No files will be modified[/yellow]\n")
    else:
        if backup:
            backup_dir = images_dir.parent / "fighters_backup"
            console.print(f"Backup directory: {backup_dir}\n")
        else:
            console.print("[yellow]⚠ No backup will be created[/yellow]\n")

        if not Confirm.ask("Proceed with normalization?"):
            console.print("[red]Cancelled[/red]")
            return

    # Process images
    stats = {
        'success': 0,
        'error': 0,
        'total_size_before': 0,
        'total_size_after': 0,
    }

    errors = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Normalizing images...", total=len(image_files))

        for img_path in image_files:
            fighter_id = img_path.stem

            # Backup original if requested
            if backup and not dry_run:
                backup_dir = images_dir.parent / "fighters_backup"
                backup_dir.mkdir(exist_ok=True)
                backup_path = backup_dir / img_path.name
                if not backup_path.exists():
                    import shutil
                    shutil.copy2(img_path, backup_path)

            # Normalize image (output as .jpg)
            output_path = images_dir / f"{fighter_id}.jpg"
            result = normalize_image(img_path, output_path, target_size, quality, dry_run)

            if result['status'] == 'success':
                stats['success'] += 1
                stats['total_size_before'] += result['file_size_before']
                if result['file_size_after']:
                    stats['total_size_after'] += result['file_size_after']

                # Remove original if it's not .jpg
                if not dry_run and img_path.suffix.lower() != '.jpg':
                    img_path.unlink()
            else:
                stats['error'] += 1
                errors.append((fighter_id, result.get('error', 'Unknown error')))

            progress.advance(task)

    # Display results
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  ✓ Success: {stats['success']}")
    console.print(f"  ✗ Errors: {stats['error']}")

    if not dry_run:
        # Calculate size reduction
        size_before_mb = stats['total_size_before'] / (1024 * 1024)
        size_after_mb = stats['total_size_after'] / (1024 * 1024)
        reduction = ((stats['total_size_before'] - stats['total_size_after']) / stats['total_size_before']) * 100

        console.print("\n[bold]Storage:[/bold]")
        console.print(f"  Before: {size_before_mb:.2f} MB")
        console.print(f"  After: {size_after_mb:.2f} MB")
        console.print(f"  Saved: {reduction:.1f}%")

    if errors:
        console.print(f"\n[red]Errors ({len(errors)}):[/red]")
        for fighter_id, error in errors[:10]:
            console.print(f"  {fighter_id}: {error}")
        if len(errors) > 10:
            console.print(f"  ... and {len(errors) - 10} more")

    if not dry_run and backup:
        console.print(f"\n[dim]Original images backed up to: {images_dir.parent / 'fighters_backup'}[/dim]")


def main():
    parser = argparse.ArgumentParser(
        description="Normalize fighter images to consistent size and format"
    )
    parser.add_argument(
        "--size",
        type=int,
        default=300,
        help="Target size (square) in pixels (default: 300)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=85,
        help="JPEG quality 1-100 (default: 85)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze images without modifying them",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backup of original images",
    )

    args = parser.parse_args()

    images_dir = Path("data/images/fighters")

    if not images_dir.exists():
        console.print(f"[red]Images directory not found: {images_dir}[/red]")
        return

    normalize_all_images(
        images_dir=images_dir,
        target_size=(args.size, args.size),
        quality=args.quality,
        dry_run=args.dry_run,
        backup=not args.no_backup,
    )


if __name__ == "__main__":
    main()
