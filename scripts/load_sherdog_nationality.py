"""
Load Sherdog nationality for all fighters from scraped data.

Usage:
    python scripts/load_sherdog_nationality.py
"""

import asyncio
import json
from pathlib import Path

import click
from sqlalchemy import select

from backend.db.connection import get_async_session_context
from backend.db.models import Fighter


@click.command()
def load_sherdog_nationality():
    """Load Sherdog nationality from sherdog_fighter_details.jsonl."""
    asyncio.run(_load_sherdog_nationality_async())


async def _load_sherdog_nationality_async():
    stats = {
        "total_scraped": 0,
        "fighters_found": 0,
        "loaded": 0,
        "skipped_no_nationality": 0,
        "skipped_not_found": 0,
        "errors": 0,
    }

    # Load scraped Sherdog data from JSONL
    sherdog_file = Path("data/processed/sherdog_fighter_details.jsonl")

    if not sherdog_file.exists():
        click.echo(f"❌ File not found: {sherdog_file}")
        return

    click.echo(f"📖 Reading {sherdog_file}...")

    # Build mapping of ufc_id -> nationality
    nationality_map = {}
    with open(sherdog_file) as f:
        for line in f:
            data = json.loads(line)
            stats["total_scraped"] += 1

            ufc_id = data.get("ufc_id")
            nationality = data.get("nationality")

            if ufc_id and nationality:
                nationality_map[ufc_id] = nationality

    click.echo(f"✅ Loaded {len(nationality_map)} nationalities from scraped data")
    click.echo(f"Starting database updates...\n")

    async with get_async_session_context() as session:
        # Get all fighters
        result = await session.execute(select(Fighter))
        all_fighters = result.scalars().all()

        click.echo(f"Found {len(all_fighters)} fighters in database")

        for fighter in all_fighters:
            if fighter.id not in nationality_map:
                stats["skipped_not_found"] += 1
                continue

            nationality = nationality_map[fighter.id]

            if not nationality:
                stats["skipped_no_nationality"] += 1
                continue

            try:
                fighter.nationality = nationality
                stats["loaded"] += 1
                stats["fighters_found"] += 1

                if stats["loaded"] % 100 == 0:
                    click.echo(f"✅ Loaded {stats['loaded']} nationalities...")

            except Exception as e:
                click.echo(f"❌ Error updating {fighter.name} ({fighter.id}): {e}")
                stats["errors"] += 1

        await session.commit()
        click.echo("\n✅ Changes committed to database")

    click.echo("\n" + "=" * 50)
    click.echo("SUMMARY")
    click.echo("=" * 50)
    click.echo(f"Total scraped records: {stats['total_scraped']}")
    click.echo(f"Nationalities available: {len(nationality_map)}")
    click.echo(f"Fighters found in DB: {stats['fighters_found']}")
    click.echo(f"Successfully loaded: {stats['loaded']}")
    click.echo(f"Skipped (no nationality): {stats['skipped_no_nationality']}")
    click.echo(f"Skipped (not in scrape): {stats['skipped_not_found']}")
    click.echo(f"Errors: {stats['errors']}")


if __name__ == "__main__":
    load_sherdog_nationality()
