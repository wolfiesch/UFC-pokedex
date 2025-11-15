"""Load UFC.com birthplace and training gym data from scraped files.

Usage:
    python scripts/load_ufc_com_birthplace.py
"""

import asyncio
import json
from pathlib import Path

import click
from sqlalchemy import select

from backend.db.connection import get_async_session_context
from backend.db.models import Fighter


@click.command()
def load_ufc_com_data():
    """Load birthplace and training gym data from UFC.com scrape."""
    asyncio.run(_load_ufc_com_data_async())


async def _load_ufc_com_data_async():
    stats = {
        "total_files": 0,
        "fighters_found": 0,
        "birthplace_loaded": 0,
        "training_loaded": 0,
        "skipped_no_data": 0,
        "skipped_not_found": 0,
        "errors": 0,
    }

    # Load scraped UFC.com data from individual JSON files
    data_dir = Path("data/processed/ufc_com_fighters")

    if not data_dir.exists():
        click.echo(f"❌ Directory not found: {data_dir}")
        return

    click.echo(f"📖 Reading from {data_dir}...")

    # Build mapping of slug -> data
    fighter_data_map = {}
    for file_path in data_dir.glob("*.json"):
        stats["total_files"] += 1
        try:
            with open(file_path) as f:
                data = json.load(f)
                slug = data.get("slug")
                if slug:
                    fighter_data_map[slug] = data
        except (json.JSONDecodeError, Exception) as e:
            click.echo(f"⚠️  Failed to read {file_path.name}: {e}")
            continue

    click.echo(f"✅ Loaded {len(fighter_data_map)} fighter profiles from files")
    click.echo(f"Starting database updates...\\n")

    async with get_async_session_context() as session:
        # Get all fighters
        result = await session.execute(select(Fighter))
        all_fighters = result.scalars().all()

        click.echo(f"Found {len(all_fighters)} fighters in database")

        for fighter in all_fighters:
            if not fighter.ufc_com_slug or fighter.ufc_com_slug not in fighter_data_map:
                stats["skipped_not_found"] += 1
                continue

            data = fighter_data_map[fighter.ufc_com_slug]

            # Extract fields
            birthplace = data.get("birthplace")
            birthplace_city = data.get("birthplace_city")
            birthplace_country = data.get("birthplace_country")
            training_gym = data.get("training_gym")
            training_city = data.get("training_city")
            training_country = data.get("training_country")
            fighting_out_of = data.get("fighting_out_of")

            # Track if we updated anything
            updated = False

            try:
                # Update birthplace fields if available
                if birthplace:
                    fighter.birthplace = birthplace
                    updated = True
                    stats["birthplace_loaded"] += 1

                if birthplace_city:
                    fighter.birthplace_city = birthplace_city

                if birthplace_country:
                    fighter.birthplace_country = birthplace_country

                # Update training fields if available
                if training_gym:
                    fighter.training_gym = training_gym
                    updated = True
                    stats["training_loaded"] += 1

                if training_city:
                    fighter.training_city = training_city

                if training_country:
                    fighter.training_country = training_country

                # Update fighting_out_of if available
                if fighting_out_of:
                    fighter.fighting_out_of = fighting_out_of
                    updated = True

                if updated:
                    stats["fighters_found"] += 1

                    if stats["fighters_found"] % 100 == 0:
                        click.echo(f"✅ Updated {stats['fighters_found']} fighters...")

                else:
                    stats["skipped_no_data"] += 1

            except Exception as e:
                click.echo(f"❌ Error updating {fighter.name} ({fighter.id}): {e}")
                stats["errors"] += 1

        await session.commit()
        click.echo("\\n✅ Changes committed to database")

    click.echo("\\n" + "=" * 50)
    click.echo("SUMMARY")
    click.echo("=" * 50)
    click.echo(f"Total JSON files read: {stats['total_files']}")
    click.echo(f"Fighter profiles loaded: {len(fighter_data_map)}")
    click.echo(f"Fighters found in DB: {stats['fighters_found']}")
    click.echo(f"Birthplace data loaded: {stats['birthplace_loaded']}")
    click.echo(f"Training gym data loaded: {stats['training_loaded']}")
    click.echo(f"Skipped (no new data): {stats['skipped_no_data']}")
    click.echo(f"Skipped (not in DB): {stats['skipped_not_found']}")
    click.echo(f"Errors: {stats['errors']}")


if __name__ == "__main__":
    load_ufc_com_data()
