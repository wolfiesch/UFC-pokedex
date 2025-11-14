"""Export fighters that have never been scraped from UFC.com.

Creates a JSONL file with UFC.com slugs for fighters missing birthplace data.

Usage:
    python scripts/export_never_scraped_ufc_com.py
"""

import asyncio
import json
from pathlib import Path

import click
from sqlalchemy import select

from backend.db.connection import get_async_session_context
from backend.db.models import Fighter


@click.command()
def export_never_scraped():
    """Export never-scraped fighters to JSONL for UFC.com scraper."""
    asyncio.run(_export_never_scraped_async())


async def _export_never_scraped_async():
    output_file = Path("data/processed/ufc_com_never_scraped.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    click.echo("🔍 Finding fighters without birthplace data...")

    async with get_async_session_context() as session:
        # Get fighters without birthplace data that have UFC.com slugs
        result = await session.execute(
            select(Fighter).where(
                (Fighter.birthplace.is_(None) | (Fighter.birthplace == ""))
                & Fighter.ufc_com_slug.isnot(None)
                & (Fighter.ufc_com_slug != "")
            )
        )
        fighters = result.scalars().all()

        click.echo(f"✅ Found {len(fighters)} fighters to scrape")

        # Write to JSONL
        with output_file.open("w") as f:
            for fighter in fighters:
                data = {
                    "slug": fighter.ufc_com_slug,
                    "ufc_id": fighter.id,
                    "name": fighter.name,
                }
                f.write(json.dumps(data) + "\n")

        click.echo(f"📝 Exported to {output_file}")
        click.echo(f"\nTo scrape these fighters, run:")
        click.echo(
            f"  .venv/bin/scrapy crawl ufc_com_athlete_detail -a input={output_file}"
        )


if __name__ == "__main__":
    export_never_scraped()
