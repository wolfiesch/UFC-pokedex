#!/usr/bin/env python
"""Manually add high-profile fighters with known Sherdog pages."""

import asyncio
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

console = Console()

# Manual mappings for high-profile fighters (UFC name -> Sherdog URL)
HIGH_PROFILE_MAPPINGS = {
    "Georges St-Pierre": "https://www.sherdog.com/fighter/Georges-St-Pierre-3500",
    "Jon Jones": "https://www.sherdog.com/fighter/Jon-Jones-27944",
    "TJ Dillashaw": "https://www.sherdog.com/fighter/TJ-Dillashaw-38553",
    "BJ Penn": "https://www.sherdog.com/fighter/BJ-Penn-1307",
    "Jacare Souza": "https://www.sherdog.com/fighter/Ronaldo-Souza-8394",
    "Renato Moicano": "https://www.sherdog.com/fighter/Renato-Moicano-80173",
    "Ovince Saint Preux": "https://www.sherdog.com/fighter/Ovince-St-Preux-38985",
    "Manvel Gamburyan": "https://www.sherdog.com/fighter/Manvel-Gamburyan-18173",
    "Loma Lookboonmee": "https://www.sherdog.com/fighter/Loma-Lookboonmee-241827",
    "Khalil Rountree Jr.": "https://www.sherdog.com/fighter/Khalil-Rountree-Jr-73859",
    "CB Dollaway": "https://www.sherdog.com/fighter/CB-Dollaway-22455",
    "Constantinos Philippou": "https://www.sherdog.com/fighter/Constantinos-Philippou-31496",
    "Aleksei Oleinik": "https://www.sherdog.com/fighter/Aleksei-Oleinik-22653",
    "Phil Rowe": "https://www.sherdog.com/fighter/Phil-Rowe-194685",
    "Godofredo Pepey": "https://www.sherdog.com/fighter/Godofredo-Pepey-85571",
}


async def get_fighter_id(name: str) -> str | None:
    """Get fighter ID from database by name."""
    from sqlalchemy import select

    from backend.db.connection import get_session
    from backend.db.models import Fighter

    async with get_session() as session:
        session: AsyncSession
        stmt = select(Fighter.id, Fighter.name).where(Fighter.name == name)
        result = await session.execute(stmt)
        rows = result.all()
        if rows:
            console.print(f"  [dim]Found ID: {rows[0][0]}[/dim]")
            return rows[0][0]
        return None


def download_image(sherdog_url: str, ufc_id: str, images_dir: Path) -> bool:
    """Download fighter image from Sherdog."""
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })

        response = session.get(sherdog_url, timeout=30)
        if response.status_code != 200:
            return False

        soup = BeautifulSoup(response.text, "html.parser")
        bio_section = soup.find("div", class_="module bio_fighter")
        if not bio_section:
            return False

        img_tag = bio_section.find("img")
        if not img_tag or not img_tag.get("src"):
            return False

        image_url = img_tag["src"]
        if not image_url.startswith("http"):
            image_url = f"https://www.sherdog.com{image_url}"

        img_response = session.get(image_url, timeout=30)
        if img_response.status_code != 200:
            return False

        ext = "png" if image_url.lower().endswith(".png") else "jpg"
        image_path = images_dir / f"{ufc_id}.{ext}"
        image_path.write_bytes(img_response.content)

        return True

    except (requests.exceptions.RequestException, OSError) as e:
        console.print(f"[red]Error downloading {sherdog_url}: {e}[/red]")
        return False


async def update_database(fighter_id: str, images_dir: Path) -> bool:
    """Update database with image URL."""
    from backend.db.connection import get_session
    from backend.db.models import Fighter

    # Find image file
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


async def main():
    """Process high-profile fighters."""
    console.print("[bold cyan]Adding High-Profile Fighters[/bold cyan]\n")

    images_dir = Path("data/images/fighters")
    images_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0

    for name, sherdog_url in HIGH_PROFILE_MAPPINGS.items():
        console.print(f"Processing {name}...")

        # Get fighter ID
        fighter_id = await get_fighter_id(name)
        if not fighter_id:
            console.print("  [yellow]⚠[/yellow] Not found in database")
            continue

        # Download image
        if download_image(sherdog_url, fighter_id, images_dir):
            # Update database
            if await update_database(fighter_id, images_dir):
                console.print("  [green]✓[/green] Downloaded and updated")
                success_count += 1
            else:
                console.print("  [red]✗[/red] Failed to update database")
        else:
            console.print("  [red]✗[/red] Failed to download image")

    console.print(f"\n[green]✓[/green] Successfully added {success_count} fighters")


if __name__ == "__main__":
    asyncio.run(main())
