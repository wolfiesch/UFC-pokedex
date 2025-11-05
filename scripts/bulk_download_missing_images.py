#!/usr/bin/env python
"""Bulk download images for all fighters missing photos."""

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

console = Console()


def download_fighter_image_from_sherdog(
    session: requests.Session,
    ufc_id: str,
    sherdog_url: str,
    images_dir: Path,
) -> tuple[str, bool, str | None]:
    """Download a single fighter's image from Sherdog."""
    try:
        # Fetch the Sherdog profile page
        response = session.get(sherdog_url, timeout=30)
        if response.status_code != 200:
            return (ufc_id, False, f"HTTP {response.status_code}")

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the bio section with fighter image
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

        # Determine file extension
        if image_url.lower().endswith(".png"):
            ext = "png"
        elif image_url.lower().endswith(".gif"):
            ext = "gif"
        else:
            ext = "jpg"

        # Save image
        image_path = images_dir / f"{ufc_id}.{ext}"
        image_path.write_bytes(img_response.content)

        return (ufc_id, True, None)

    except Exception as e:
        return (ufc_id, False, str(e))


async def bulk_update_database(fighter_ids: list[str], images_dir: Path):
    """Bulk update database with image URLs."""
    from backend.db.connection import get_session
    from backend.db.models import Fighter

    updated_count = 0

    async with get_session() as session:
        session: AsyncSession

        for fighter_id in fighter_ids:
            # Check which file extension exists
            image_path = None
            for ext in ['jpg', 'png', 'gif']:
                file_path = images_dir / f"{fighter_id}.{ext}"
                if file_path.exists():
                    image_path = f"images/fighters/{fighter_id}.{ext}"
                    break

            if image_path:
                stmt = (
                    update(Fighter)
                    .where(Fighter.id == fighter_id)
                    .values(
                        image_url=image_path,
                        image_scraped_at=datetime.utcnow(),
                    )
                )
                await session.execute(stmt)
                updated_count += 1

        await session.commit()

    return updated_count


def main():
    """Main entry point."""
    console.print("[bold cyan]Bulk Download Missing Fighter Images[/bold cyan]\n")

    # Load Sherdog mapping
    mapping_file = Path("data/sherdog_id_mapping.json")
    if not mapping_file.exists():
        console.print(f"[red]Error:[/red] Mapping file not found: {mapping_file}")
        return

    with mapping_file.open() as f:
        sherdog_mapping = json.load(f)

    console.print(f"Loaded Sherdog mapping for {len(sherdog_mapping)} fighters")

    # Load list of fighters missing images
    missing_ids_file = Path("/tmp/missing_image_ids.txt")
    if not missing_ids_file.exists():
        console.print("[red]Error:[/red] Missing IDs file not found")
        console.print("Run: psql ... -c \"SELECT id FROM fighters WHERE image_url IS NULL;\" > /tmp/missing_image_ids.txt")
        return

    with missing_ids_file.open() as f:
        missing_ids = [line.strip() for line in f if line.strip()]

    console.print(f"Found {len(missing_ids)} fighters missing images\n")

    # Filter to only fighters in Sherdog mapping
    fighters_to_download = {}
    fighters_not_in_mapping = []

    for fighter_id in missing_ids:
        if fighter_id in sherdog_mapping:
            fighters_to_download[fighter_id] = sherdog_mapping[fighter_id]
        else:
            fighters_not_in_mapping.append(fighter_id)

    console.print(f"[green]✓[/green] {len(fighters_to_download)} fighters in Sherdog mapping")
    console.print(f"[yellow]⚠[/yellow] {len(fighters_not_in_mapping)} fighters NOT in Sherdog mapping")
    console.print()

    if len(fighters_to_download) == 0:
        console.print("[yellow]No fighters to download from Sherdog[/yellow]")
        return

    # Create images directory
    images_dir = Path("data/images/fighters")
    images_dir.mkdir(parents=True, exist_ok=True)

    # Setup session with browser-like headers
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })

    # Download images in parallel (with rate limiting)
    success_count = 0
    failure_count = 0
    failures = []
    successfully_downloaded = []

    console.print(f"[bold]Downloading {len(fighters_to_download)} images...[/bold]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading...", total=len(fighters_to_download))

        # Use ThreadPoolExecutor for parallel downloads
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all download tasks
            future_to_fighter = {}
            for ufc_id, data in fighters_to_download.items():
                sherdog_url = data.get("sherdog_url")
                if sherdog_url:
                    future = executor.submit(
                        download_fighter_image_from_sherdog,
                        session,
                        ufc_id,
                        sherdog_url,
                        images_dir
                    )
                    future_to_fighter[future] = ufc_id

            # Process completed downloads
            for future in as_completed(future_to_fighter):
                fighter_id, success, error = future.result()

                if success:
                    success_count += 1
                    successfully_downloaded.append(fighter_id)
                else:
                    failure_count += 1
                    failures.append((fighter_id, error))

                progress.advance(task)

                # Small delay to be respectful
                time.sleep(0.5)

    # Print summary
    console.print("\n[bold]Download Summary:[/bold]")
    console.print(f"[green]✓[/green] Successfully downloaded: {success_count}")

    if failure_count > 0:
        console.print(f"[red]✗[/red] Failed: {failure_count}")
        if failure_count <= 10:
            console.print("\n[bold]Failures:[/bold]")
            for fighter_id, error in failures[:10]:
                console.print(f"  - {fighter_id}: {error}")

    # Update database
    if success_count > 0:
        console.print("\n[bold cyan]Updating database...[/bold cyan]")
        updated_count = asyncio.run(bulk_update_database(successfully_downloaded, images_dir))
        console.print(f"[green]✓[/green] Updated {updated_count} fighters in database")

    # Save list of fighters not in mapping for follow-up
    if fighters_not_in_mapping:
        not_in_mapping_file = Path("data/fighters_not_in_sherdog_mapping.txt")
        not_in_mapping_file.write_text("\n".join(fighters_not_in_mapping))
        console.print(f"\n[yellow]⚠[/yellow] Saved {len(fighters_not_in_mapping)} fighter IDs not in mapping to:")
        console.print(f"   {not_in_mapping_file}")


if __name__ == "__main__":
    main()
