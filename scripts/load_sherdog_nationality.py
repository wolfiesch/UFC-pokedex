"""
Load Sherdog nationality for fighters without UFC.com matches.

Usage:
    python scripts/load_sherdog_nationality.py
"""

import asyncio
import json
from pathlib import Path

import click

from backend.db.connection import get_async_session_context
from backend.db.repositories.fighter_repository import FighterRepository


@click.command()
def load_sherdog_nationality():
    """Load Sherdog nationality for fighters without UFC.com data."""
    asyncio.run(_load_sherdog_nationality_async())


async def _load_sherdog_nationality_async():
    stats = {"total": 0, "loaded": 0, "no_data": 0, "errors": 0}

    async with get_async_session_context() as session:
        repo = FighterRepository(session)

        # Find fighters without UFC.com data
        fighters = await repo.get_fighters_without_ufc_com_data()
        stats["total"] = len(fighters)

        click.echo(f"Found {stats['total']} fighters without UFC.com data")

        for fighter in fighters:
            if not fighter.sherdog_id:
                stats["no_data"] += 1
                continue

            # Load Sherdog data
            sherdog_file = (
                Path("data/processed/sherdog_fighters") / f"{fighter.sherdog_id}.json"
            )

            if not sherdog_file.exists():
                stats["no_data"] += 1
                continue

            with open(sherdog_file) as f:
                sherdog_data = json.load(f)

            nationality = sherdog_data.get("nationality")

            if nationality:
                try:
                    await repo.update_fighter_nationality(
                        fighter_id=fighter.id, nationality=nationality
                    )
                    stats["loaded"] += 1

                    if stats["loaded"] % 100 == 0:
                        click.echo(f"Loaded {stats['loaded']} nationalities...")

                except Exception as e:
                    click.echo(f"❌ Error updating {fighter.id}: {e}")
                    stats["errors"] += 1
            else:
                stats["no_data"] += 1

        await session.commit()
        click.echo("✅ Changes committed to database")

    click.echo("\n" + "=" * 50)
    click.echo("SUMMARY")
    click.echo("=" * 50)
    for key, value in stats.items():
        click.echo(f"{key}: {value}")


if __name__ == "__main__":
    load_sherdog_nationality()
