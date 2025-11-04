#!/usr/bin/env python
"""Download fighter images from Sherdog for fighters missing images."""

import json
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def download_fighter_image(
    session: requests.Session,
    ufc_id: str,
    sherdog_url: str,
    images_dir: Path,
) -> tuple[str, bool, str | None]:
    """Download a single fighter's image from Sherdog.

    Args:
        session: requests session with browser-like headers
        ufc_id: UFC fighter ID (used as filename)
        sherdog_url: Sherdog profile URL
        images_dir: Directory to save images

    Returns:
        Tuple of (fighter_id, success, error_message)
    """
    try:
        # Fetch the Sherdog profile page
        response = session.get(sherdog_url, timeout=30)
        if response.status_code != 200:
            return (ufc_id, False, f"HTTP {response.status_code}")

        html = response.text

        # Parse HTML to find the fighter image
        soup = BeautifulSoup(html, "html.parser")

        # Find the bio section with the fighter image
        bio_section = soup.find("div", class_="module bio_fighter")
        if not bio_section:
            bio_section = soup.find("div", class_="bio_fighter")

        if not bio_section:
            return (ufc_id, False, "Bio section not found")

        # Extract image URL
        img_tag = bio_section.find("img")
        if not img_tag or not img_tag.get("src"):
            return (ufc_id, False, "Image tag not found")

        image_url = img_tag["src"]

        # Convert relative URL to absolute
        if not image_url.startswith("http"):
            image_url = f"https://www.sherdog.com{image_url}"

        # Download the image
        img_response = session.get(image_url, timeout=30)
        if img_response.status_code != 200:
            return (ufc_id, False, f"Image HTTP {img_response.status_code}")

        image_data = img_response.content

        # Determine file extension
        if image_url.lower().endswith(".png"):
            ext = "png"
        elif image_url.lower().endswith(".gif"):
            ext = "gif"
        else:
            ext = "jpg"

        # Save image
        image_path = images_dir / f"{ufc_id}.{ext}"
        image_path.write_bytes(image_data)

        return (ufc_id, True, None)

    except Exception as e:
        return (ufc_id, False, str(e))


def main():
    """Main entry point."""
    console.print("[bold cyan]Downloading Missing Fighter Images[/bold cyan]\n")

    # Load the temporary mapping file
    mapping_file = Path("data/temp_sherdog_mapping.json")
    if not mapping_file.exists():
        console.print(f"[red]Error:[/red] Mapping file not found: {mapping_file}")
        sys.exit(1)

    with mapping_file.open() as f:
        mapping = json.load(f)

    console.print(f"Loaded mapping for {len(mapping)} fighters\n")

    # Create images directory
    images_dir = Path("data/images/fighters")
    images_dir.mkdir(parents=True, exist_ok=True)

    # Setup requests session with browser-like headers
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })

    success_count = 0
    failure_count = 0
    failures = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading images...", total=len(mapping))

        # Download images with delay between requests
        for ufc_id, data in mapping.items():
            sherdog_url = data["sherdog_url"]
            fighter_id, success, error = download_fighter_image(
                session, ufc_id, sherdog_url, images_dir
            )

            if success:
                success_count += 1
                console.print(f"[green]✓[/green] Downloaded {fighter_id}")
            else:
                failure_count += 1
                failures.append((fighter_id, error))
                console.print(f"[red]✗[/red] Failed {fighter_id}: {error}")

            progress.advance(task)

            # Add delay to be respectful to Sherdog's servers
            time.sleep(2)

    # Print summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"[green]✓[/green] Successfully downloaded: {success_count}")
    if failure_count > 0:
        console.print(f"[red]✗[/red] Failed: {failure_count}")
        console.print("\n[bold]Failures:[/bold]")
        for fighter_id, error in failures:
            console.print(f"  - {fighter_id}: {error}")


if __name__ == "__main__":
    main()
