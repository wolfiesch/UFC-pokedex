#!/usr/bin/env python
"""Smart image finder that searches multiple sources dynamically."""

import asyncio
import re
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession

console = Console()


def normalize_fighter_name(name: str) -> str:
    """Normalize fighter name for URL search."""
    # Remove nicknames in quotes
    name = re.sub(r'"[^"]*"', '', name)
    # Replace St. with St, St- with St
    name = name.replace("St.", "St").replace("St-", "St")
    # Remove special characters except spaces and hyphens
    name = re.sub(r'[^\w\s-]', '', name)
    # Strip and collapse spaces
    name = ' '.join(name.split())
    return name


def search_sherdog_for_fighter(session: requests.Session, fighter_name: str) -> str | None:
    """Search Sherdog for fighter and return profile URL."""
    try:
        normalized_name = normalize_fighter_name(fighter_name)

        # Try direct URL construction (common pattern)
        url_name = normalized_name.replace(' ', '-').replace('--', '-')
        possible_urls = [
            f"https://www.sherdog.com/fighter/{url_name}",
            f"https://www.sherdog.com/fighter/{url_name.replace('-', '')}",
        ]

        for url in possible_urls:
            try:
                response = session.head(url, timeout=10, allow_redirects=True)
                if response.status_code == 200 and '/fighter/' in response.url:
                    return response.url
            except:
                continue

        # Fall back to search
        search_url = f"https://www.sherdog.com/stats/fightfinder?SearchTxt={quote(normalized_name)}"
        response = session.get(search_url, timeout=15)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # Look for fighter links
            fighter_links = soup.find_all('a', href=re.compile(r'/fighter/[^/]+-\d+'))
            if fighter_links:
                return f"https://www.sherdog.com{fighter_links[0]['href']}"

        return None

    except Exception as e:
        return None


def download_image_from_url(
    session: requests.Session,
    ufc_id: str,
    profile_url: str,
    images_dir: Path,
    source: str = "sherdog"
) -> tuple[str, bool, str | None]:
    """Download fighter image from profile URL."""
    try:
        # Fetch profile page
        response = session.get(profile_url, timeout=30)
        if response.status_code != 200:
            return (ufc_id, False, f"HTTP {response.status_code}")

        soup = BeautifulSoup(response.text, "html.parser")

        # Find image based on source
        img_tag = None
        if source == "sherdog":
            bio_section = soup.find("div", class_="module bio_fighter")
            if bio_section:
                img_tag = bio_section.find("img")

        if not img_tag or not img_tag.get("src"):
            return (ufc_id, False, "Image not found")

        image_url = img_tag["src"]
        if not image_url.startswith("http"):
            base = "https://www.sherdog.com" if source == "sherdog" else ""
            image_url = f"{base}{image_url}"

        # Download image
        img_response = session.get(image_url, timeout=30)
        if img_response.status_code != 200:
            return (ufc_id, False, f"Image HTTP {img_response.status_code}")

        # Save image
        ext = "png" if image_url.lower().endswith(".png") else "jpg"
        image_path = images_dir / f"{ufc_id}.{ext}"
        image_path.write_bytes(img_response.content)

        return (ufc_id, True, None)

    except Exception as e:
        return (ufc_id, False, str(e))


def process_fighter(
    session: requests.Session,
    fighter_data: dict,
    images_dir: Path,
) -> tuple[str, bool, str | None]:
    """Search for and download a single fighter's image."""
    ufc_id = fighter_data['id']
    name = fighter_data['name']

    # Search Sherdog
    profile_url = search_sherdog_for_fighter(session, name)

    if profile_url:
        return download_image_from_url(session, ufc_id, profile_url, images_dir)

    return (ufc_id, False, "Not found on Sherdog")


async def get_fighters_without_images() -> list[dict]:
    """Get list of fighters missing images from database."""
    from backend.db.connection import get_session
    from backend.db.models import Fighter

    async with get_session() as session:
        session: AsyncSession
        stmt = select(Fighter.id, Fighter.name, Fighter.record).where(
            Fighter.image_url.is_(None)
        ).order_by(select(Fighter.id).correlate(Fighter).scalar_subquery())

        result = await session.execute(stmt)
        fighters = [
            {"id": row.id, "name": row.name, "record": row.record}
            for row in result.all()
        ]

        return fighters


async def bulk_update_database(fighter_ids: list[str], images_dir: Path) -> int:
    """Bulk update database with image URLs."""
    from backend.db.connection import get_session
    from backend.db.models import Fighter

    updated_count = 0

    async with get_session() as session:
        session: AsyncSession

        for fighter_id in fighter_ids:
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
    console.print("[bold cyan]Smart Fighter Image Finder[/bold cyan]\n")

    # Get fighters from database
    console.print("Loading fighters from database...")
    fighters = asyncio.run(get_fighters_without_images())
    console.print(f"Found {len(fighters)} fighters missing images\n")

    if not fighters:
        console.print("[green]All fighters have images![/green]")
        return

    # Limit to top N fighters to avoid rate limiting (process in batches)
    batch_size = 100
    fighters_batch = fighters[:batch_size]
    console.print(f"Processing batch of {len(fighters_batch)} fighters\n")

    # Create images directory
    images_dir = Path("data/images/fighters")
    images_dir.mkdir(parents=True, exist_ok=True)

    # Setup session
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

    success_count = 0
    failure_count = 0
    successfully_downloaded = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Searching and downloading...", total=len(fighters_batch))

        # Process fighters with rate limiting
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_fighter = {}

            for fighter in fighters_batch:
                future = executor.submit(process_fighter, session, fighter, images_dir)
                future_to_fighter[future] = fighter

            for future in as_completed(future_to_fighter):
                fighter = future_to_fighter[future]
                fighter_id, success, error = future.result()

                if success:
                    success_count += 1
                    successfully_downloaded.append(fighter_id)
                    console.print(f"[green]✓[/green] {fighter['name']}")
                else:
                    failure_count += 1

                progress.advance(task)
                time.sleep(1.5)  # Rate limit

    # Update database
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"[green]✓[/green] Successfully downloaded: {success_count}")
    console.print(f"[red]✗[/red] Failed: {failure_count}")

    if success_count > 0:
        console.print(f"\n[bold cyan]Updating database...[/bold cyan]")
        updated_count = asyncio.run(bulk_update_database(successfully_downloaded, images_dir))
        console.print(f"[green]✓[/green] Updated {updated_count} fighters in database")

        remaining = len(fighters) - batch_size
        if remaining > 0:
            console.print(f"\n[yellow]Note:[/yellow] {remaining} fighters remaining. Run script again to process next batch.")


if __name__ == "__main__":
    main()
