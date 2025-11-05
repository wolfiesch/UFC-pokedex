#!/usr/bin/env python
"""Download images for fighters that are in Sherdog mapping but missing images."""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

console = Console()


async def get_fighters_missing_images() -> list[str]:
    """Get fighter IDs that are missing images from database."""
    from backend.db.connection import get_session
    from backend.db.models import Fighter

    async with get_session() as session:
        session: AsyncSession
        stmt = select(Fighter.id).where(Fighter.image_url.is_(None))
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]


def download_image(session: requests.Session, fighter_id: str, sherdog_url: str, images_dir: Path) -> bool:
    """Download a single fighter's image."""
    try:
        response = session.get(sherdog_url, timeout=30)
        if response.status_code != 200:
            return False

        soup = BeautifulSoup(response.text, "html.parser")
        bio = soup.find("div", class_="module bio_fighter")
        if not bio:
            return False

        img = bio.find("img")
        if not img or not img.get("src"):
            return False

        img_url = img["src"]
        if not img_url.startswith("http"):
            img_url = f"https://www.sherdog.com{img_url}"

        img_response = session.get(img_url, timeout=30)
        if img_response.status_code != 200:
            return False

        ext = "png" if img_url.lower().endswith(".png") else "jpg"
        (images_dir / f"{fighter_id}.{ext}").write_bytes(img_response.content)
        return True

    except Exception:
        return False


async def update_database(fighter_ids: list[str], images_dir: Path) -> int:
    """Update database with image URLs."""
    from sqlalchemy import update

    from backend.db.connection import get_session
    from backend.db.models import Fighter

    updated = 0
    async with get_session() as session:
        session: AsyncSession

        for fighter_id in fighter_ids:
            image_path = None
            for ext in ['jpg', 'png', 'gif']:
                if (images_dir / f"{fighter_id}.{ext}").exists():
                    image_path = f"images/fighters/{fighter_id}.{ext}"
                    break

            if image_path:
                stmt = update(Fighter).where(Fighter.id == fighter_id).values(
                    image_url=image_path,
                    image_scraped_at=datetime.utcnow()
                )
                await session.execute(stmt)
                updated += 1

        await session.commit()
    return updated


async def main():
    """Main entry point."""
    console.print("[bold cyan]Downloading Final Missing Images[/bold cyan]\n")

    # Load Sherdog mapping
    mapping_file = Path("data/sherdog_id_mapping.json")
    with mapping_file.open() as f:
        sherdog_mapping = json.load(f)

    console.print(f"Sherdog mapping: {len(sherdog_mapping)} fighters")

    # Get fighters missing images
    missing_ids = await get_fighters_missing_images()
    console.print(f"Database missing images: {len(missing_ids)} fighters\n")

    # Find intersection
    to_download = {}
    for fighter_id in missing_ids:
        if fighter_id in sherdog_mapping:
            sherdog_url = sherdog_mapping[fighter_id].get("sherdog_url")
            if sherdog_url:
                to_download[fighter_id] = sherdog_url

    console.print(f"[green]Found {len(to_download)} fighters in Sherdog mapping to download[/green]\n")

    if len(to_download) == 0:
        console.print("[yellow]No fighters to download from Sherdog mapping[/yellow]")
        console.print(f"\n[dim]The remaining {len(missing_ids)} fighters are not in Sherdog mapping.[/dim]")
        return

    # Download images
    images_dir = Path("data/images/fighters")
    images_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })

    success = []
    for fighter_id, sherdog_url in to_download.items():
        console.print(f"Downloading {fighter_id}...", end=" ")

        if download_image(session, fighter_id, sherdog_url, images_dir):
            console.print("[green]✓[/green]")
            success.append(fighter_id)
        else:
            console.print("[red]✗[/red]")

        time.sleep(2)

    # Update database
    if success:
        console.print("\n[bold]Updating database...[/bold]")
        updated = await update_database(success, images_dir)
        console.print(f"[green]✓[/green] Updated {updated} fighters\n")

    # Final stats
    remaining = len(missing_ids) - len(success)
    console.print("[bold]Final Status:[/bold]")
    console.print(f"  Successfully downloaded: {len(success)}")
    console.print(f"  Still missing: {remaining}")
    console.print(f"  Coverage: {(4447 - remaining) / 4447 * 100:.2f}%")


if __name__ == "__main__":
    asyncio.run(main())
