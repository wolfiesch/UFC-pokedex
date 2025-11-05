#!/usr/bin/env python
"""Quickly update fighter records without full detail scraping."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
from dotenv import load_dotenv
from parsel import Selector
from rich.console import Console
from rich.progress import Progress
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import get_session
from backend.db.models import Fighter
from scraper.utils.parser import clean_text

load_dotenv()

console = Console()


async def fetch_fighter_record(
    client: httpx.AsyncClient, fighter_id: str, url: str
) -> tuple[str, str | None]:
    """Fetch only the record field from a fighter's detail page."""
    try:
        response = await client.get(url, timeout=10.0)
        if response.status_code != 200:
            return fighter_id, None

        html = response.text
        selector = Selector(text=html)

        # Use the fixed selector
        hero = selector.css(".b-content__banner") or selector.css(".b-content__title")
        record_text = clean_text(hero.css("span.b-content__title-record::text").get())

        if record_text and ":" in record_text:
            record = record_text.split(":")[-1].strip()
            return fighter_id, record
        return fighter_id, record_text

    except Exception as e:
        console.print(f"[yellow]Error fetching {fighter_id}: {e}[/yellow]")
        return fighter_id, None


async def update_records_in_db(db_session: AsyncSession, records: dict[str, str]) -> int:
    """Bulk update fighter records in database."""
    updated = 0
    for fighter_id, record in records.items():
        if record:
            await db_session.execute(
                update(Fighter).where(Fighter.id == fighter_id).values(record=record)
            )
            updated += 1

    await db_session.commit()
    return updated


async def update_records_in_json(fighters_dir: Path, records: dict[str, str]) -> int:
    """Update fighter records in JSON files."""
    updated = 0
    for fighter_id, record in records.items():
        if not record:
            continue

        json_path = fighters_dir / f"{fighter_id}.json"
        if json_path.exists():
            try:
                with open(json_path) as f:
                    data = json.load(f)

                data["record"] = record

                with open(json_path, "w") as f:
                    json.dump(data, f, indent=2)

                updated += 1
            except Exception as e:
                console.print(f"[yellow]Error updating JSON for {fighter_id}: {e}[/yellow]")

    return updated


async def main(limit: int | None = None) -> None:
    console.print("[bold blue]UFC Fighter Record Updater[/bold blue]\n")

    # Load fighter list
    list_path = Path("data/processed/fighters_list.jsonl")
    if not list_path.exists():
        console.print("[red]fighters_list.jsonl not found![/red]")
        return

    fighters = []
    with open(list_path) as f:
        for line in f:
            data = json.loads(line)
            fighters.append((data["fighter_id"], data["detail_url"]))
            if limit and len(fighters) >= limit:
                break

    if limit:
        console.print(f"[yellow]TEST MODE: Processing first {len(fighters)} fighters[/yellow]\n")
    else:
        console.print(f"Found {len(fighters)} fighters to update\n")

    # Fetch records with high concurrency
    records: dict[str, str] = {}
    headers = {"User-Agent": "UFC-Pokedex-Scraper/0.1"}
    limits = httpx.Limits(max_connections=30, max_keepalive_connections=20)

    async with httpx.AsyncClient(headers=headers, limits=limits) as client:
        with Progress(console=console) as progress:
            task = progress.add_task("[cyan]Fetching records...", total=len(fighters))

            # Process in batches to avoid overwhelming the server
            batch_size = 100
            for i in range(0, len(fighters), batch_size):
                batch = fighters[i : i + batch_size]

                tasks = [fetch_fighter_record(client, fid, url) for fid, url in batch]
                results = await asyncio.gather(*tasks)

                for fighter_id, record in results:
                    if record:
                        records[fighter_id] = record

                progress.update(task, advance=len(batch))

                # Small delay between batches to be respectful
                if i + batch_size < len(fighters):
                    await asyncio.sleep(0.5)

    console.print(f"\n[green]✓ Fetched {len(records)} records[/green]\n")

    # Update database
    console.print("[cyan]Updating database...[/cyan]")
    async with get_session() as db_session:
        db_updated = await update_records_in_db(db_session, records)
    console.print(f"[green]✓ Updated {db_updated} fighters in database[/green]\n")

    # Update JSON files
    fighters_dir = Path("data/processed/fighters")
    if fighters_dir.exists():
        console.print("[cyan]Updating JSON files...[/cyan]")
        json_updated = await update_records_in_json(fighters_dir, records)
        console.print(f"[green]✓ Updated {json_updated} JSON files[/green]\n")

    console.print("[bold green]Record update complete![/bold green]")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Update fighter records from UFCStats")
    parser.add_argument(
        "--limit",
        type=int,
        help="Only update first N fighters (for testing)",
    )
    args = parser.parse_args()

    asyncio.run(main(limit=args.limit))
