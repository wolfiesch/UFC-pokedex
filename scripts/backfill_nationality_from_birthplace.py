"""Backfill nationality from birthplace_country when nationality is missing.

For fighters where Sherdog didn't have nationality data but we have birthplace_country
from UFC.com, we can derive the nationality ISO code.

Usage:
    python scripts/backfill_nationality_from_birthplace.py
"""

import asyncio
import sys
from pathlib import Path

import click
from sqlalchemy import select

# Add scraper to path to use the normalize_nationality function
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.connection import get_async_session_context
from backend.db.models import Fighter
from scraper.utils.country_mapping import normalize_nationality


@click.command()
def backfill_nationality():
    """Backfill nationality from birthplace_country."""
    asyncio.run(_backfill_nationality_async())


async def _backfill_nationality_async():
    stats = {
        "total_missing_nationality": 0,
        "has_birthplace_country": 0,
        "successfully_backfilled": 0,
        "no_iso_mapping": 0,
        "errors": 0,
    }

    click.echo("🔍 Finding fighters with missing nationality but have birthplace_country...")

    async with get_async_session_context() as session:
        # Get fighters with no nationality but have birthplace_country
        result = await session.execute(
            select(Fighter).where(
                (Fighter.nationality.is_(None) | (Fighter.nationality == ""))
                & Fighter.birthplace_country.isnot(None)
                & (Fighter.birthplace_country != "")
            )
        )
        fighters = result.scalars().all()

        stats["total_missing_nationality"] = len(fighters)
        click.echo(f"✅ Found {len(fighters)} fighters to backfill\n")

        for fighter in fighters:
            stats["has_birthplace_country"] += 1

            try:
                # Convert birthplace_country to ISO code
                iso_code = normalize_nationality(fighter.birthplace_country)

                if iso_code:
                    fighter.nationality = iso_code
                    stats["successfully_backfilled"] += 1

                    if stats["successfully_backfilled"] % 50 == 0:
                        click.echo(
                            f"  ✅ Backfilled {stats['successfully_backfilled']} nationalities..."
                        )
                else:
                    stats["no_iso_mapping"] += 1
                    click.echo(
                        f"  ⚠️  No ISO mapping for: {fighter.name} ({fighter.birthplace_country})"
                    )

            except Exception as e:
                click.echo(f"  ❌ Error processing {fighter.name}: {e}")
                stats["errors"] += 1

        await session.commit()
        click.echo("\n✅ Changes committed to database")

    click.echo("\n" + "=" * 50)
    click.echo("SUMMARY")
    click.echo("=" * 50)
    click.echo(f"Fighters with missing nationality: {stats['total_missing_nationality']}")
    click.echo(f"Had birthplace_country: {stats['has_birthplace_country']}")
    click.echo(f"Successfully backfilled: {stats['successfully_backfilled']}")
    click.echo(f"No ISO mapping found: {stats['no_iso_mapping']}")
    click.echo(f"Errors: {stats['errors']}")

    if stats["successfully_backfilled"] > 0:
        new_coverage_count = 3929 + stats["successfully_backfilled"]
        new_coverage_pct = round(new_coverage_count * 100.0 / 4669, 1)
        click.echo(f"\n🎯 New nationality coverage: {new_coverage_pct}% ({new_coverage_count}/4669)")


if __name__ == "__main__":
    backfill_nationality()
