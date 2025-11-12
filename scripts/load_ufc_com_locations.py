"""
Load UFC.com location data into fighters table.

Usage:
    python scripts/load_ufc_com_locations.py --matches data/processed/ufc_com_matches.jsonl
    python scripts/load_ufc_com_locations.py --dry-run  # Preview changes
    python scripts/load_ufc_com_locations.py --auto-only  # Skip manual review items
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import click
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from backend.db.connection import get_async_session_context
from backend.db.repositories.fighter_repository import FighterRepository
from scripts.utils.gym_locations import resolve_gym_location


@click.command()
@click.option(
    "--matches", type=click.Path(exists=True), required=True, help="Path to matches JSONL file"
)
@click.option("--dry-run", is_flag=True, help="Preview changes without writing")
@click.option("--auto-only", is_flag=True, help="Skip manual review items")
def load_ufc_com_locations(matches: str, dry_run: bool, auto_only: bool):
    """Load UFC.com location data into fighters table."""
    asyncio.run(_load_ufc_com_locations_async(matches, dry_run, auto_only))


async def _load_ufc_com_locations_async(matches: str, dry_run: bool, auto_only: bool):
    stats = {
        "total_matches": 0,
        "loaded": 0,
        "skipped_manual_review": 0,
        "skipped_low_confidence": 0,
        "errors": 0,
    }

    async with get_async_session_context() as session:
        repo = FighterRepository(session)

        with open(matches) as f:
            for line in f:
                match = json.loads(line)
                stats["total_matches"] += 1

                # Skip if needs manual review and auto_only is set
                if auto_only and match.get("needs_manual_review"):
                    stats["skipped_manual_review"] += 1
                    continue

                # Skip low confidence matches
                if match["confidence"] < 70:
                    stats["skipped_low_confidence"] += 1
                    continue

                # Load UFC.com fighter data
                ufc_com_file = (
                    Path("data/processed/ufc_com_fighters") / f"{match['ufc_com_slug']}.json"
                )

                if not ufc_com_file.exists():
                    click.echo(f"⚠️  Missing UFC.com data for {match['ufc_com_slug']}")
                    stats["errors"] += 1
                    continue

                with open(ufc_com_file) as uf:
                    ufc_com_data = json.load(uf)

                gym_location = resolve_gym_location(ufc_com_data.get("training_gym"))

                if dry_run:
                    click.echo(f"Would update {match['ufcstats_id']} with:")
                    click.echo(f"  Birthplace: {ufc_com_data.get('birthplace')}")
                    click.echo(f"  Training gym: {ufc_com_data.get('training_gym')}")
                    if gym_location:
                        click.echo(
                            f"  Training location: {gym_location.city}, {gym_location.country}"
                        )
                else:
                    try:
                        update_kwargs: dict[str, Any] = {
                            "fighter_id": match["ufcstats_id"],
                            "ufc_com_slug": match["ufc_com_slug"],
                            "ufc_com_match_confidence": match["confidence"],
                            "ufc_com_match_method": match["classification"],
                            "ufc_com_scraped_at": datetime.utcnow(),
                            "needs_manual_review": match.get("needs_manual_review"),
                        }

                        for field in (
                            "birthplace",
                            "birthplace_city",
                            "birthplace_country",
                            "nationality",
                            "training_gym",
                        ):
                            value = ufc_com_data.get(field)
                            if value:
                                update_kwargs[field] = value

                        if gym_location:
                            if gym_location.city:
                                update_kwargs.setdefault("training_city", gym_location.city)
                            if gym_location.country:
                                update_kwargs.setdefault(
                                    "training_country", gym_location.country
                                )

                        await repo.update_fighter_location(**update_kwargs)
                        await session.commit()  # Commit after each successful update
                        stats["loaded"] += 1

                        if stats["loaded"] % 100 == 0:
                            click.echo(f"Loaded {stats['loaded']} fighters...")

                    except Exception as e:
                        await session.rollback()
                        click.echo(f"❌ Error updating {match['ufcstats_id']}: {e}")
                        stats["errors"] += 1

        if not dry_run:
            click.echo("✅ All changes committed to database")

    click.echo("\n" + "=" * 50)
    click.echo("SUMMARY")
    click.echo("=" * 50)
    for key, value in stats.items():
        click.echo(f"{key}: {value}")


if __name__ == "__main__":
    load_ufc_com_locations()
