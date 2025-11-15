#!/usr/bin/env python
"""
Multi-source image scraper orchestrator.

Cascades through multiple sources in priority order:
1. Wikimedia Commons (legal, ~20% coverage)
2. Sherdog via existing mapping (high UFC fighter coverage)
3. Tapology (MMA database, similar to Sherdog)
4. Bing Image Search (alternative to DuckDuckGo)
5. Manual review for remainder
"""

# IMPORTANT: Load environment variables FIRST before any other imports
from dotenv import load_dotenv

load_dotenv()

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

console = Console()

# Load Sherdog mapping once at startup
SHERDOG_MAPPING_FILE = Path("data/sherdog_id_mapping.json")
SHERDOG_MAPPING = {}

if SHERDOG_MAPPING_FILE.exists():
    SHERDOG_MAPPING = json.loads(SHERDOG_MAPPING_FILE.read_text())
    console.print(f"[dim]Loaded Sherdog mapping: {len(SHERDOG_MAPPING)} fighters[/dim]")


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


def search_wikimedia_commons(fighter_name: str) -> str | None:
    """Search Wikimedia Commons for fighter image."""
    try:
        api_url = "https://commons.wikimedia.org/w/api.php"
        search_params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": f"{fighter_name} UFC",
            "srnamespace": "6",
            "srlimit": "5",
        }

        headers = {
            "User-Agent": "UFC-Pokedex-Scraper/0.1 (+https://github.com/wolfiesch/ufc-pokedex)",
        }

        response = requests.get(api_url, params=search_params, headers=headers, timeout=15)
        if response.status_code != 200:
            return None

        data = response.json()
        search_results = data.get("query", {}).get("search", [])
        if not search_results:
            return None

        # Get image URL for first result
        title = search_results[0]["title"]
        imageinfo_params = {
            "action": "query",
            "format": "json",
            "prop": "imageinfo",
            "titles": title,
            "iiprop": "url|size|mime",
        }

        response = requests.get(api_url, params=imageinfo_params, headers=headers, timeout=15)
        if response.status_code != 200:
            return None

        data = response.json()
        pages = data.get("query", {}).get("pages", {})

        for page in pages.values():
            if "imageinfo" in page:
                imageinfo = page["imageinfo"][0]
                mime = imageinfo.get("mime", "")
                if mime.startswith("image/"):
                    return imageinfo.get("url")

    except Exception as e:
        console.print(f"    [dim]Wikimedia error: {str(e)[:50]}[/dim]")

    return None


def get_sherdog_image(fighter_id: str) -> str | None:
    """Get Sherdog image URL from mapping and scrape the page."""
    try:
        # Check if fighter is in mapping
        if fighter_id not in SHERDOG_MAPPING:
            return None

        fighter_url = SHERDOG_MAPPING[fighter_id]["sherdog_url"]

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        # Get fighter page
        response = requests.get(fighter_url, headers=headers, timeout=20)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Find bio image
        bio = soup.select_one("div.module.bio_fighter")
        if not bio:
            return None

        img = bio.select_one("img")
        if not img or not img.get("src"):
            return None

        img_url = img["src"]
        if not img_url.startswith("http"):
            img_url = f"https://www.sherdog.com{img_url}"

        return img_url

    except Exception as e:
        console.print(f"    [dim]Sherdog error: {str(e)[:50]}[/dim]")

    return None


def search_tapology(fighter_name: str) -> str | None:
    """Search Tapology for fighter image."""
    try:
        # Build search URL
        search_query = fighter_name.replace(" ", "-").lower()
        search_url = f"https://www.tapology.com/search?term={fighter_name.replace(' ', '+')}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        # Search for fighter
        response = requests.get(search_url, headers=headers, timeout=20)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Find first fighter result
        fighter_link = soup.select_one("a.name[href*='/fightcenter/fighters/']")
        if not fighter_link:
            return None

        fighter_url = fighter_link["href"]
        if not fighter_url.startswith("http"):
            fighter_url = f"https://www.tapology.com{fighter_url}"

        # Get fighter page
        time.sleep(2)  # Rate limit
        response = requests.get(fighter_url, headers=headers, timeout=20)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Find fighter image
        img = soup.select_one("img.fighter_profile_image, img.profile_image")
        if not img or not img.get("src"):
            return None

        img_url = img["src"]
        if not img_url.startswith("http"):
            img_url = f"https://www.tapology.com{img_url}"

        # Skip placeholder images
        if "default" in img_url.lower() or "placeholder" in img_url.lower():
            return None

        return img_url

    except Exception as e:
        console.print(f"    [dim]Tapology error: {str(e)[:50]}[/dim]")

    return None


def search_bing_images(fighter_name: str, nickname: str | None = None) -> str | None:
    """Search Bing Images for fighter photo."""
    try:
        # Build search query. Including the fighter's nickname (when available)
        # helps steer Bing toward the correct athlete instead of famous namesakes.
        nickname_fragment = ""
        if nickname:
            sanitized = nickname.strip().replace('"', "")
            if sanitized:
                nickname_fragment = f' "{sanitized}"'

        query = f"{fighter_name}{nickname_fragment} MMA UFC fighter"

        # Bing Image Search API endpoint (free tier available)
        # For now, use HTML scraping approach
        search_url = f"https://www.bing.com/images/search?q={query.replace(' ', '+')}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        response = requests.get(search_url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Find first image result
        # Bing uses data attributes for image URLs
        img = soup.select_one("a.iusc")
        if not img:
            return None

        # Parse the m parameter which contains JSON with image URL
        m_param = img.get("m")
        if not m_param:
            return None

        import json
        try:
            img_data = json.loads(m_param)
            img_url = img_data.get("murl") or img_data.get("turl")
            if img_url:
                return img_url
        except:
            pass

        return None

    except Exception as e:
        console.print(f"    [dim]Bing error: {str(e)[:50]}[/dim]")

    return None


def download_image(image_url: str, fighter_id: str, images_dir: Path, source: str) -> bool:
    """Download image from URL and save to disk."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }

        response = requests.get(image_url, headers=headers, timeout=30, stream=True)

        if response.status_code == 200:
            content = response.content

            # Validate image size
            if len(content) < 5000:  # Less than 5KB
                return False

            # Determine extension
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
        console.print(f"    [red]Download error ({source}): {str(e)[:50]}[/red]")

    return False


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


async def scrape_fighter_image(
    fighter: dict,
    images_dir: Path
) -> tuple[str, bool, str, str]:
    """
    Try multiple sources in cascade to find fighter image.

    Returns: (fighter_id, success, message, source)
    """
    fighter_id = fighter["id"]
    fighter_name = fighter["name"]

    # Source 1: Wikimedia Commons (legal, ~20% coverage)
    console.print("  [dim]Trying Wikimedia Commons...[/dim]")
    image_url = search_wikimedia_commons(fighter_name)

    if image_url:
        if download_image(image_url, fighter_id, images_dir, "wikimedia"):
            db_updated = await update_database(fighter_id, images_dir)
            if db_updated:
                return (fighter_id, True, "Downloaded", "Wikimedia Commons")

    time.sleep(1)  # Brief pause between sources

    # Source 2: Sherdog via mapping (high UFC coverage)
    console.print("  [dim]Trying Sherdog (from mapping)...[/dim]")
    image_url = get_sherdog_image(fighter_id)

    if image_url:
        if download_image(image_url, fighter_id, images_dir, "sherdog"):
            db_updated = await update_database(fighter_id, images_dir)
            if db_updated:
                return (fighter_id, True, "Downloaded", "Sherdog")

    time.sleep(1)

    # Source 3: Tapology (MMA database)
    console.print("  [dim]Trying Tapology...[/dim]")
    image_url = search_tapology(fighter_name)

    if image_url:
        if download_image(image_url, fighter_id, images_dir, "tapology"):
            db_updated = await update_database(fighter_id, images_dir)
            if db_updated:
                return (fighter_id, True, "Downloaded", "Tapology")

    time.sleep(1)

    # Source 4: Bing Image Search
    console.print("  [dim]Trying Bing Images...[/dim]")
    fighter_nickname = (fighter.get("nickname") or "").strip() or None

    image_url = search_bing_images(fighter_name, fighter_nickname)

    if image_url:
        if download_image(image_url, fighter_id, images_dir, "bing"):
            db_updated = await update_database(fighter_id, images_dir)
            if db_updated:
                return (fighter_id, True, "Downloaded", "Bing Images")

    # All sources exhausted
    return (fighter_id, False, "No image found", "None")


async def main(batch_size: int = 50, test_mode: bool = False):
    """Main orchestrator entry point."""
    console.print("[bold cyan]Multi-Source Fighter Image Scraper[/bold cyan]")
    console.print("[dim]Sources: Wikimedia Commons → Sherdog → Tapology → Bing Images[/dim]\n")

    # Get fighters
    limit = 10 if test_mode else batch_size
    fighters = await get_fighters_without_images(limit=limit)

    if not fighters:
        console.print("[green]✓ All fighters have images![/green]")
        return

    console.print(f"Found {len(fighters)} fighters missing images")

    if test_mode:
        console.print("[yellow]⚠ Running in TEST MODE (10 fighters only)[/yellow]\n")

    # Setup
    images_dir = Path("data/images/fighters")
    images_dir.mkdir(parents=True, exist_ok=True)

    # Track progress by source
    success_count = 0
    fail_count = 0
    source_stats = {
        "Wikimedia Commons": 0,
        "Sherdog": 0,
        "Tapology": 0,
        "Bing Images": 0,
        "None": 0,
    }
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

            console.print(f"\n[bold]{idx + 1}/{len(fighters)}[/bold] {fighter_name}")

            # Try all sources
            fid, success, message, source = await scrape_fighter_image(fighter, images_dir)

            if success:
                console.print(f"  [green]✓[/green] {message} from {source}")
                success_count += 1
            else:
                console.print(f"  [red]✗[/red] {message}")
                fail_count += 1

            source_stats[source] += 1

            results.append({
                "fighter_id": fid,
                "name": fighter_name,
                "success": success,
                "message": message,
                "source": source,
            })

            progress.advance(task)

            # Rate limiting - 3 seconds between fighters
            time.sleep(3)

    # Final report
    console.print("\n[bold]Final Results:[/bold]")
    console.print(f"  [green]✓[/green] Success: {success_count}/{len(fighters)}")
    console.print(f"  [red]✗[/red] Failed: {fail_count}/{len(fighters)}")
    console.print(f"  [cyan]→[/cyan] Success rate: {success_count / len(fighters) * 100:.1f}%")

    console.print("\n[bold]By Source:[/bold]")
    console.print(f"  Wikimedia Commons: {source_stats['Wikimedia Commons']}")
    console.print(f"  Sherdog: {source_stats['Sherdog']}")
    console.print(f"  Tapology: {source_stats['Tapology']}")
    console.print(f"  Bing Images: {source_stats['Bing Images']}")
    console.print(f"  Failed: {source_stats['None']}")

    # Save results
    results_file = Path("data/logs/orchestrator_results.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.write_text(json.dumps({
        "timestamp": datetime.utcnow().isoformat(),
        "total": len(fighters),
        "success": success_count,
        "failed": fail_count,
        "source_stats": source_stats,
        "results": results,
    }, indent=2))

    console.print(f"\n[dim]Results saved to: {results_file}[/dim]")

    # List fighters needing manual review
    if fail_count > 0:
        console.print(f"\n[yellow]Fighters needing manual review ({fail_count}):[/yellow]")
        for result in results:
            if not result["success"]:
                console.print(f"  - {result['name']} ({result['fighter_id']})")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Multi-source fighter image scraper")
    parser.add_argument("--batch-size", type=int, default=50, help="Number of fighters to process")
    parser.add_argument("--test", action="store_true", help="Test mode (10 fighters only)")

    args = parser.parse_args()

    asyncio.run(main(batch_size=args.batch_size, test_mode=args.test))
