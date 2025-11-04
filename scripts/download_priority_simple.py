#!/usr/bin/env python
"""Simple script to download priority fighter images."""

import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()

FIGHTERS = {
    "6506c1d34da9c013": "https://www.sherdog.com/fighter/Georges-St-Pierre-3500",
    "07f72a2a7591b409": "https://www.sherdog.com/fighter/Jon-Jones-27944",
    "c849740a3ff51931": "https://www.sherdog.com/fighter/TJ-Dillashaw-38553",
    "73c7cfa551289285": "https://www.sherdog.com/fighter/BJ-Penn-1307",
    "5d7bdab5e03e3216": "https://www.sherdog.com/fighter/CB-Dollaway-22455",
    "749f572d1d3161fb": "https://www.sherdog.com/fighter/Khalil-Rountree-Jr-73859",
    "98c23cb6da5b3352": "https://www.sherdog.com/fighter/Aleksei-Oleinik-22653",
    "8e382b585a92affe": "https://www.sherdog.com/fighter/Phil-Rowe-194685",
}

def main():
    console.print("[bold cyan]Downloading Priority Fighters[/bold cyan]\n")

    images_dir = Path("data/images/fighters")
    images_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })

    success = 0

    for fighter_id, sherdog_url in FIGHTERS.items():
        console.print(f"Processing {fighter_id}...")

        try:
            response = session.get(sherdog_url, timeout=30)
            soup = BeautifulSoup(response.text, "html.parser")

            bio = soup.find("div", class_="module bio_fighter")
            if not bio:
                console.print("  [red]✗[/red] Bio not found")
                continue

            img = bio.find("img")
            if not img or not img.get("src"):
                console.print("  [red]✗[/red] Image not found")
                continue

            img_url = img["src"]
            if not img_url.startswith("http"):
                img_url = f"https://www.sherdog.com{img_url}"

            img_response = session.get(img_url, timeout=30)
            if img_response.status_code == 200:
                (images_dir / f"{fighter_id}.jpg").write_bytes(img_response.content)
                console.print("  [green]✓[/green] Downloaded")
                success += 1
            else:
                console.print(f"  [red]✗[/red] HTTP {img_response.status_code}")

        except Exception as e:
            console.print(f"  [red]✗[/red] Error: {e}")

        time.sleep(2)

    console.print(f"\n[green]✓[/green] Downloaded {success}/{len(FIGHTERS)} fighters")
    console.print("\nRun: PYTHONPATH=. .venv/bin/python scripts/sync_images_to_db.py")

if __name__ == "__main__":
    main()
