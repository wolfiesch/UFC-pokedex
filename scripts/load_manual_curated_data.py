"""
Load manually curated location data for historical fighters.

Usage:
    python scripts/load_manual_curated_data.py --csv data/manual/legends_locations.csv
"""

import asyncio
import csv

import click

from backend.db.connection import get_async_session_context
from backend.db.repositories.fighter_repository import FighterRepository


@click.command()
@click.option(
    "--csv",
    "csv_file",
    type=click.Path(exists=True),
    required=True,
    help="Path to CSV file with manual data",
)
def load_manual_curated_data(csv_file: str):
    """Load manually curated location data."""
    asyncio.run(_load_manual_curated_data_async(csv_file))


async def _load_manual_curated_data_async(csv_file: str):
    stats = {"total": 0, "loaded": 0, "errors": 0}

    async with get_async_session_context() as session:
        repo = FighterRepository(session)

        with open(csv_file) as f:
            reader = csv.DictReader(f)

            for row in reader:
                stats["total"] += 1

                try:
                    # Parse birthplace into city and country if available
                    birthplace = row.get("birthplace")
                    birthplace_city = None
                    birthplace_country = None

                    if birthplace:
                        if "," in birthplace:
                            parts = birthplace.split(",", 1)
                            birthplace_city = parts[0].strip()
                            birthplace_country = parts[1].strip()
                        else:
                            birthplace_country = birthplace.strip()

                    await repo.update_fighter_location(
                        fighter_id=row["ufcstats_id"],
                        birthplace=birthplace,
                        birthplace_city=birthplace_city,
                        birthplace_country=birthplace_country,
                        nationality=row.get("nationality"),
                        training_gym=row.get("training_gym"),
                        ufc_com_match_method="manual",
                        ufc_com_match_confidence=100.0,
                    )
                    stats["loaded"] += 1
                    click.echo(f"✅ Loaded manual data for {row['name']}")

                except Exception as e:
                    click.echo(f"❌ Error loading {row['name']}: {e}")
                    stats["errors"] += 1

        await session.commit()
        click.echo("✅ Changes committed to database")

    click.echo("\n" + "=" * 50)
    click.echo("SUMMARY")
    click.echo("=" * 50)
    for key, value in stats.items():
        click.echo(f"{key}: {value}")


if __name__ == "__main__":
    load_manual_curated_data()
