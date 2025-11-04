#!/usr/bin/env python
"""Validate fighter images using basic image recognition checks."""

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()


def validate_image(image_path: Path) -> Dict[str, any]:
    """
    Validate a fighter image using basic checks.

    Returns dict with:
        - valid: bool
        - issues: list of strings
        - details: dict of metrics
    """
    issues = []
    details = {}

    try:
        img = Image.open(image_path)

        # Basic checks
        width, height = img.size
        details['width'] = width
        details['height'] = height
        details['format'] = img.format
        details['mode'] = img.mode

        # Check 1: Minimum size (should be at least 50x50)
        if width < 50 or height < 50:
            issues.append(f"Too small ({width}x{height})")

        # Check 2: Maximum size (sanity check - not larger than 5000x5000)
        if width > 5000 or height > 5000:
            issues.append(f"Too large ({width}x{height})")

        # Check 3: Aspect ratio (fighters should be roughly portrait or square, not super wide)
        aspect_ratio = width / height
        details['aspect_ratio'] = round(aspect_ratio, 2)

        if aspect_ratio > 3.0:
            issues.append(f"Too wide (aspect ratio {aspect_ratio:.2f})")
        elif aspect_ratio < 0.3:
            issues.append(f"Too tall (aspect ratio {aspect_ratio:.2f})")

        # Check 4: File size (should be reasonable, not 0 bytes or massive)
        file_size = image_path.stat().st_size
        details['file_size'] = file_size

        if file_size < 1000:  # Less than 1KB is suspicious
            issues.append(f"File too small ({file_size} bytes)")
        elif file_size > 50 * 1024 * 1024:  # More than 50MB is excessive
            issues.append(f"File too large ({file_size / 1024 / 1024:.1f}MB)")

        # Check 5: Color mode (should be RGB or have color)
        if img.mode == '1':  # 1-bit black and white
            issues.append("Black and white only")

        # Check 6: Image entropy (complexity) - very low entropy might indicate placeholder
        import numpy as np
        try:
            # Convert to grayscale for entropy calculation
            if img.mode != 'L':
                gray = img.convert('L')
            else:
                gray = img

            # Calculate histogram
            histogram = gray.histogram()
            histogram = np.array(histogram, dtype=float)
            histogram = histogram / histogram.sum()

            # Calculate entropy
            entropy = -np.sum(histogram * np.log2(histogram + 1e-10))
            details['entropy'] = round(entropy, 2)

            # Very low entropy (< 3.0) might indicate a placeholder or simple graphic
            if entropy < 3.0:
                issues.append(f"Low complexity (entropy {entropy:.2f})")
        except Exception:
            # Skip entropy check if it fails
            pass

        # Check 7: Dominant color (images that are mostly one color might be placeholders)
        try:
            # Get color distribution
            colors = img.convert('RGB').getcolors(maxcolors=1000000)
            if colors:
                # Sort by frequency
                colors.sort(reverse=True, key=lambda x: x[0])

                # Calculate percentage of most common color
                total_pixels = width * height
                most_common_pct = (colors[0][0] / total_pixels) * 100
                details['dominant_color_pct'] = round(most_common_pct, 1)

                # If more than 80% is one color, it's suspicious
                if most_common_pct > 80:
                    issues.append(f"Single color dominates ({most_common_pct:.1f}%)")
        except Exception:
            # Skip color check if it fails
            pass

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'details': details,
        }

    except Exception as e:
        return {
            'valid': False,
            'issues': [f"Cannot open image: {str(e)}"],
            'details': {},
        }


def validate_all_images(
    images_dir: Path,
    fighter_ids: List[str] = None,
    show_all: bool = False,
) -> Tuple[List[str], List[Tuple[str, List[str]]]]:
    """
    Validate all fighter images or specific ones.

    Returns:
        - valid_ids: list of fighter IDs with valid images
        - invalid_ids: list of (fighter_id, issues) tuples
    """
    console.print("[bold cyan]Validating Fighter Images[/bold cyan]\n")

    # Get image files
    if fighter_ids:
        image_files = []
        for fighter_id in fighter_ids:
            for ext in ['jpg', 'jpeg', 'png', 'gif']:
                img_path = images_dir / f"{fighter_id}.{ext}"
                if img_path.exists():
                    image_files.append(img_path)
                    break
    else:
        image_files = []
        for ext in ['jpg', 'jpeg', 'png', 'gif']:
            image_files.extend(images_dir.glob(f"*.{ext}"))

    console.print(f"Validating {len(image_files)} images...\n")

    valid_ids = []
    invalid_ids = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Validating images...", total=len(image_files))

        for img_path in image_files:
            fighter_id = img_path.stem
            result = validate_image(img_path)

            if result['valid']:
                valid_ids.append(fighter_id)
            else:
                invalid_ids.append((fighter_id, result['issues'], result['details']))

            progress.advance(task)

    # Display results
    console.print(f"\n[bold]Validation Results:[/bold]")
    console.print(f"  ✓ Valid: {len(valid_ids)}")
    console.print(f"  ✗ Invalid: {len(invalid_ids)}")

    if invalid_ids:
        console.print(f"\n[yellow]Invalid Images ({len(invalid_ids)}):[/yellow]\n")

        table = Table()
        table.add_column("Fighter ID", style="cyan")
        table.add_column("Issues", style="red")
        table.add_column("Details", style="dim")

        for fighter_id, issues, details in invalid_ids if show_all else invalid_ids[:20]:
            issue_str = ", ".join(issues)
            detail_str = f"{details.get('width', '?')}x{details.get('height', '?')}"
            if 'file_size' in details:
                detail_str += f", {details['file_size'] / 1024:.1f}KB"

            table.add_row(fighter_id, issue_str, detail_str)

        if len(invalid_ids) > 20 and not show_all:
            table.add_row("...", f"and {len(invalid_ids) - 20} more", "")

        console.print(table)

        # Save invalid IDs to file
        output_file = Path("data/invalid_fighter_images.txt")
        with open(output_file, "w") as f:
            for fighter_id, issues, _ in invalid_ids:
                f.write(f"{fighter_id}\n")

        console.print(f"\n[green]✓ Saved {len(invalid_ids)} invalid IDs to: {output_file}[/green]")

    return valid_ids, invalid_ids


def main():
    parser = argparse.ArgumentParser(
        description="Validate fighter images using basic image recognition"
    )
    parser.add_argument(
        "--ids-file",
        type=str,
        help="File with fighter IDs to validate (one per line)",
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Show all invalid images (not just first 20)",
    )

    args = parser.parse_args()

    images_dir = Path("data/images/fighters")

    if not images_dir.exists():
        console.print(f"[red]Images directory not found: {images_dir}[/red]")
        return

    # Get fighter IDs if file specified
    fighter_ids = None
    if args.ids_file:
        ids_path = Path(args.ids_file)
        if ids_path.exists():
            with open(ids_path) as f:
                fighter_ids = [line.strip() for line in f if line.strip()]
            console.print(f"Validating {len(fighter_ids)} fighters from {args.ids_file}\n")

    # Validate images
    valid_ids, invalid_ids = validate_all_images(
        images_dir,
        fighter_ids=fighter_ids,
        show_all=args.show_all,
    )

    # Show statistics
    if invalid_ids:
        console.print(f"\n[bold]Common Issues:[/bold]")

        issue_counts = {}
        for _, issues, _ in invalid_ids:
            for issue in issues:
                # Extract issue type
                issue_type = issue.split('(')[0].strip()
                issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1

        for issue_type, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
            console.print(f"  {issue_type}: {count}")


if __name__ == "__main__":
    main()
