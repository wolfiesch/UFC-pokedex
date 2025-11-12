#!/usr/bin/env python3
"""Extract UFC fighters that need Sherdog fight history enrichment.

This script identifies all UFC fighters in our database who DON'T have Sherdog data yet,
preparing them for comprehensive fight history scraping across all promotions.

Usage:
    python scripts/extract_ufc_fighters_for_sherdog.py [--limit N]
"""

import asyncio
import json
import os
from pathlib import Path

import click
from sqlalchemy import text

from backend.db.connection import get_session


async def get_ufc_fighters_without_sherdog(limit: int | None = None):
    """Get all UFC fighters that don't have Sherdog IDs yet.

    Args:
        limit: Optional limit on number of fighters to return

    Returns:
        List of fighter dicts with: id, name, nickname, record
    """
    async with get_session() as session:
        query = """
        SELECT
            id,
            name,
            nickname,
            record,
            division
        FROM fighters
        WHERE sherdog_id IS NULL
        ORDER BY name ASC
        """

        if limit:
            query += f" LIMIT {limit}"

        result = await session.execute(text(query))
        fighters = result.fetchall()

        fighter_list = []
        for f in fighters:
            # Parse record to get fight counts
            wins, losses, draws = 0, 0, 0
            if f.record:
                parts = f.record.replace("(", "").replace(")", "").split("-")
                if len(parts) >= 2:
                    wins = int(parts[0]) if parts[0].isdigit() else 0
                    losses = int(parts[1]) if parts[1].isdigit() else 0
                    if len(parts) >= 3:
                        draws = int(parts[2]) if parts[2].isdigit() else 0

            fighter_list.append({
                "id": f.id,
                "name": f.name,
                "nickname": f.nickname,
                "record": f.record,
                "division": f.division,
                "wins": wins,
                "losses": losses,
                "draws": draws,
                "total_fights": wins + losses + draws,
            })

        return fighter_list


async def get_database_stats():
    """Get database statistics."""
    async with get_session() as session:
        result = await session.execute(
            text("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN sherdog_id IS NULL THEN 1 END) as without_sherdog,
                COUNT(CASE WHEN sherdog_id IS NOT NULL THEN 1 END) as with_sherdog
            FROM fighters
            """)
        )
        stats = result.fetchone()

        return {
            "total_fighters": stats.total,
            "without_sherdog": stats.without_sherdog,
            "with_sherdog": stats.with_sherdog,
            "percentage_missing": round((stats.without_sherdog / stats.total * 100), 1) if stats.total else 0,
        }


@click.command()
@click.option("--limit", type=int, default=None, help="Limit number of fighters to extract (for testing)")
@click.option("--output", type=str, default="data/processed/ufc_fighters_for_sherdog.json", help="Output file path")
def main(limit: int | None, output: str):
    """Extract UFC fighters that need Sherdog enrichment."""

    async def run():
        click.echo("=" * 70)
        click.echo("EXTRACTING UFC FIGHTERS FOR SHERDOG ENRICHMENT")
        click.echo("=" * 70)
        click.echo()

        # Get database stats
        stats = await get_database_stats()

        click.echo("📊 Database Statistics:")
        click.echo(f"   Total fighters:          {stats['total_fighters']:,}")
        click.echo(f"   With Sherdog data:       {stats['with_sherdog']:,} ({100 - stats['percentage_missing']:.1f}%)")
        click.echo(f"   Without Sherdog data:    {stats['without_sherdog']:,} ({stats['percentage_missing']:.1f}%)")
        click.echo()

        # Get fighters to scrape
        if limit:
            click.echo(f"🔍 Extracting {limit:,} fighters (TEST MODE)...")
        else:
            click.echo(f"🔍 Extracting all {stats['without_sherdog']:,} fighters without Sherdog data...")

        fighters = await get_ufc_fighters_without_sherdog(limit)

        click.echo(f"✅ Extracted {len(fighters):,} fighters")
        click.echo()

        # Calculate fighter statistics
        total_fights = sum(f["total_fights"] for f in fighters)
        avg_fights = total_fights / len(fighters) if fighters else 0

        click.echo("📈 Fighter Statistics:")
        click.echo(f"   Total fights (UFC only):  {total_fights:,}")
        click.echo(f"   Average fights per fighter: {avg_fights:.1f}")
        click.echo()

        # Show top 10 fighters by fight count
        click.echo("🥊 Top 10 Fighters by Fight Count:")
        for i, fighter in enumerate(fighters[:10], 1):
            name = fighter["name"]
            nickname = f' "{fighter["nickname"]}"' if fighter["nickname"] else ""
            record = fighter["record"] or "Unknown"
            fights = fighter["total_fights"]
            click.echo(f"   {i:2}. {name}{nickname:30} - {record:15} ({fights} fights)")
        click.echo()

        # Save to file
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "metadata": {
                "extracted_at": "11/12/2025",
                "source": "UFC database fighters without Sherdog IDs",
                "total_extracted": len(fighters),
                "database_stats": stats,
                "is_test": limit is not None,
                "test_limit": limit,
            },
            "fighters": fighters,
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        click.echo(f"💾 Saved to: {output_path}")
        click.echo()

        # Estimate scraping time
        estimated_minutes = len(fighters) * 3 / 60  # ~3 seconds per fighter with rate limiting
        estimated_hours = estimated_minutes / 60

        click.echo("=" * 70)
        click.echo("⏱️  SCRAPING TIME ESTIMATE")
        click.echo("=" * 70)
        click.echo(f"Fighters to scrape:     {len(fighters):,}")
        click.echo(f"Rate limiting:          ~3 seconds per fighter")
        click.echo(f"Estimated time:         {estimated_minutes:.0f} minutes ({estimated_hours:.1f} hours)")
        click.echo()
        click.echo("💡 Recommendation: Run in batches of 500-1000 fighters")
        click.echo()

        click.echo("=" * 70)
        click.echo("✅ READY TO SCRAPE")
        click.echo("=" * 70)
        click.echo()

        if limit:
            click.echo("Next step (TEST):")
            click.echo(f"  make scrape-ufc-sherdog-test")
        else:
            click.echo("Next steps:")
            click.echo(f"  make scrape-ufc-sherdog-incremental  # Scrape unscraped fighters")
            click.echo(f"  make load-sherdog-fight-history      # Load into database")
        click.echo()

    asyncio.run(run())


if __name__ == "__main__":
    # Ensure we're using PostgreSQL
    db_url = os.getenv("DATABASE_URL")
    if not db_url or "postgresql" not in db_url:
        click.echo("❌ ERROR: DATABASE_URL not set or not PostgreSQL", err=True)
        click.echo("   Run: export DATABASE_URL=postgresql+psycopg://ufc_pokedex:ufc_pokedex@localhost:5432/ufc_pokedex", err=True)
        exit(1)

    main()
