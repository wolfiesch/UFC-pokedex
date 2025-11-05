#!/usr/bin/env python
"""Scrape fighter images from Wikimedia Commons using their official API."""

# IMPORTANT: Load environment variables FIRST before any other imports
from dotenv import load_dotenv

load_dotenv()

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

import requests
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

console = Console()


async def get_fighters_without_images(limit: int | None = None) -> list[dict]:
    """Get fighters missing images from database."""
    from backend.db.connection import get_session
    from backend.db.models import Fighter

    async with get_session() as session:
        session: AsyncSession
        stmt = select(Fighter.id, Fighter.name, Fighter.nickname).where(
            Fighter.image_url.is_(None)
        )

        if limit:
            stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        return [
            {"id": row.id, "name": row.name, "nickname": row.nickname}
            for row in result.all()
        ]


def search_wikimedia_commons(fighter_name: str, nickname: str | None = None) -> list[dict]:
    """
    Search Wikimedia Commons for fighter images using MediaWiki API.

    Returns list of image results with URL, dimensions, and metadata.
    """
    # Build search query
    query = f"{fighter_name} UFC"
    if nickname:
        query = f'{fighter_name} "{nickname}" UFC'

    # MediaWiki API endpoint
    api_url = "https://commons.wikimedia.org/w/api.php"

    # Step 1: Search for pages
    search_params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "srnamespace": "6",  # File namespace
        "srlimit": "10",
        "srinfo": "",
        "srprop": "",
    }

    headers = {
        "User-Agent": "UFC-Pokedex-Scraper/0.1 (+https://github.com/wolfiesch/ufc-pokedex)",
    }

    try:
        # Search for files
        response = requests.get(api_url, params=search_params, headers=headers, timeout=15)
        if response.status_code != 200:
            return []

        data = response.json()
        search_results = data.get("query", {}).get("search", [])

        if not search_results:
            return []

        # Step 2: Get image info for found files
        titles = [result["title"] for result in search_results[:5]]  # Top 5 results

        imageinfo_params = {
            "action": "query",
            "format": "json",
            "prop": "imageinfo",
            "titles": "|".join(titles),
            "iiprop": "url|size|mime",
            "iiurlwidth": "800",
        }

        response = requests.get(api_url, params=imageinfo_params, headers=headers, timeout=15)
        if response.status_code != 200:
            return []

        data = response.json()
        pages = data.get("query", {}).get("pages", {})

        # Format results
        images = []
        for page_id, page in pages.items():
            if "imageinfo" not in page:
                continue

            imageinfo = page["imageinfo"][0]

            # Only include actual images (not PDFs, videos, etc.)
            mime = imageinfo.get("mime", "")
            if not mime.startswith("image/"):
                continue

            images.append({
                "url": imageinfo.get("url", ""),
                "thumbnail": imageinfo.get("thumburl", ""),
                "title": page.get("title", ""),
                "width": imageinfo.get("width", 0),
                "height": imageinfo.get("height", 0),
                "mime": mime,
                "source": "wikimedia",
            })

        return images

    except Exception as e:
        console.print(f"  [yellow]Search error: {e}[/yellow]")

    return []


def download_image(image_url: str, fighter_id: str, images_dir: Path) -> bool:
    """Download image from URL and save to disk."""
    try:
        headers = {
            "User-Agent": "UFC-Pokedex-Scraper/0.1 (+https://github.com/wolfiesch/ufc-pokedex)",
        }

        response = requests.get(image_url, headers=headers, timeout=30, stream=True)

        if response.status_code == 200:
            content = response.content

            # Validate image size
            if len(content) < 5000:  # Less than 5KB - probably not a real image
                return False

            # Determine extension from content type
            content_type = response.headers.get("Content-Type", "")
            if "png" in content_type:
                ext = "png"
            elif "gif" in content_type:
                ext = "gif"
            else:
                ext = "jpg"

            # Save image
            image_path = images_dir / f"{fighter_id}.{ext}"
            image_path.write_bytes(content)

            return True
    except Exception as e:
        console.print(f"    [red]Download error: {str(e)[:50]}[/red]")

    return False


def select_best_image(images: list[dict]) -> dict | None:
    """Select the best quality image from search results."""
    if not images:
        return None

    # Filter by minimum dimensions
    MIN_WIDTH = 300
    MIN_HEIGHT = 300

    quality_images = [
        img for img in images
        if img.get("width", 0) >= MIN_WIDTH and img.get("height", 0) >= MIN_HEIGHT
    ]

    if not quality_images:
        # Fall back to any image
        quality_images = images

    # Prefer JPG/PNG over GIF
    for img in quality_images:
        mime = img.get("mime", "")
        if "jpeg" in mime or "png" in mime:
            return img

    # Return first available
    return quality_images[0] if quality_images else images[0]


async def update_database(fighter_id: str, images_dir: Path) -> bool:
    """Update database with image URL for fighter."""
    from backend.db.connection import get_session
    from backend.db.models import Fighter

    # Find saved image file
    image_path = None
    for ext in ['jpg', 'png', 'gif']:
        file_path = images_dir / f"{fighter_id}.{ext}"
        if file_path.exists():
            image_path = f"images/fighters/{fighter_id}.{ext}"
            break

    if not image_path:
        return False

    async with get_session() as session:
        session: AsyncSession

        stmt = (
            update(Fighter)
            .where(Fighter.id == fighter_id)
            .values(
                image_url=image_path,
                image_scraped_at=datetime.utcnow(),
            )
        )

        await session.execute(stmt)
        await session.commit()

    return True


def save_checkpoint(checkpoint_file: Path, data: dict):
    """Save progress checkpoint."""
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_file.write_text(json.dumps(data, indent=2))


def load_checkpoint(checkpoint_file: Path) -> dict:
    """Load progress checkpoint."""
    if checkpoint_file.exists():
        return json.loads(checkpoint_file.read_text())
    return {}


async def scrape_fighter_image(
    fighter: dict,
    images_dir: Path,
    retry_count: int = 3
) -> tuple[str, bool, str]:
    """
    Scrape image for a single fighter from Wikimedia Commons.

    Returns: (fighter_id, success, message)
    """
    fighter_id = fighter["id"]
    fighter_name = fighter["name"]
    nickname = fighter.get("nickname")

    # Try different search strategies
    search_attempts = [
        (fighter_name, nickname),
        (fighter_name, None),  # Without nickname
    ]

    for attempt_num, (name, nick) in enumerate(search_attempts):
        # Search for images
        images = search_wikimedia_commons(name, nick)

        if not images:
            if attempt_num < len(search_attempts) - 1:
                continue  # Try next search strategy
            return (fighter_id, False, "No images found")

        # Select best image
        best_image = select_best_image(images)
        if not best_image:
            return (fighter_id, False, "No suitable image")

        # Try to download
        for retry in range(retry_count):
            success = download_image(best_image["url"], fighter_id, images_dir)

            if success:
                # Update database
                db_updated = await update_database(fighter_id, images_dir)
                if db_updated:
                    return (fighter_id, True, "Downloaded from Wikimedia Commons")
                else:
                    return (fighter_id, False, "Failed to update database")

            if retry < retry_count - 1:
                time.sleep(1)  # Wait before retry

        # If first attempt failed, try next search strategy
        if attempt_num < len(search_attempts) - 1:
            continue

    return (fighter_id, False, "Download failed after retries")


async def main(batch_size: int = 50, test_mode: bool = False):
    """Main scraper entry point."""
    console.print("[bold cyan]Wikimedia Commons Fighter Image Scraper[/bold cyan]\n")

    # Get fighters
    limit = 5 if test_mode else batch_size
    fighters = await get_fighters_without_images(limit=limit)

    if not fighters:
        console.print("[green]✓ All fighters have images![/green]")
        return

    console.print(f"Found {len(fighters)} fighters missing images")

    if test_mode:
        console.print("[yellow]⚠ Running in TEST MODE (5 fighters only)[/yellow]\n")

    # Setup
    images_dir = Path("data/images/fighters")
    images_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_file = Path("data/checkpoints/wikimedia_scraper.json")
    checkpoint = load_checkpoint(checkpoint_file)

    # Track progress
    success_count = 0
    fail_count = 0
    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Scraping images...", total=len(fighters))

        for idx, fighter in enumerate(fighters):
            fighter_id = fighter["id"]
            fighter_name = fighter["name"]

            console.print(f"\n[bold]{idx + 1}/{len(fighters)}[/bold] {fighter_name} ({fighter_id})")

            # Scrape
            fid, success, message = await scrape_fighter_image(fighter, images_dir)

            if success:
                console.print(f"  [green]✓[/green] {message}")
                success_count += 1
            else:
                console.print(f"  [red]✗[/red] {message}")
                fail_count += 1

            results.append({
                "fighter_id": fid,
                "name": fighter_name,
                "success": success,
                "message": message,
            })

            progress.advance(task)

            # Checkpoint every 10 fighters
            if (idx + 1) % 10 == 0:
                save_checkpoint(checkpoint_file, {
                    "last_processed": fighter_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "results": results,
                })

            # Rate limiting - be respectful to Wikimedia
            time.sleep(1.5)  # 1.5 seconds between requests

    # Final report
    console.print("\n[bold]Final Results:[/bold]")
    console.print(f"  [green]✓[/green] Success: {success_count}/{len(fighters)}")
    console.print(f"  [red]✗[/red] Failed: {fail_count}/{len(fighters)}")
    console.print(f"  [cyan]→[/cyan] Success rate: {success_count / len(fighters) * 100:.1f}%")

    # Save final results
    results_file = Path("data/logs/wikimedia_scraper_results.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.write_text(json.dumps({
        "timestamp": datetime.utcnow().isoformat(),
        "total": len(fighters),
        "success": success_count,
        "failed": fail_count,
        "results": results,
    }, indent=2))

    console.print(f"\n[dim]Results saved to: {results_file}[/dim]")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape fighter images from Wikimedia Commons")
    parser.add_argument("--batch-size", type=int, default=50, help="Number of fighters to process")
    parser.add_argument("--test", action="store_true", help="Test mode (5 fighters only)")

    args = parser.parse_args()

    asyncio.run(main(batch_size=args.batch_size, test_mode=args.test))
