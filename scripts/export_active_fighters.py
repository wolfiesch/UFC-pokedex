#!/usr/bin/env python
"""Export active UFC fighters to JSON for Sherdog matching."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import get_session
from backend.db.models import Fighter

# Load environment variables
load_dotenv()

console = Console()


async def export_active_fighters(limit: int | None = None):
    """Export active fighters to JSON file.

    Args:
        limit: Optional limit on number of fighters to export (for testing)
    """
    output_file = Path("data/active_fighters.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    async with get_session() as session:
        session: AsyncSession

        # Query fighters from database
        # For now, we'll export all fighters as we don't have an "active" flag
        # We could filter by recent fight activity if needed
        query = select(Fighter).order_by(Fighter.name)

        if limit:
            query = query.limit(limit)

        result = await session.execute(query)
        fighters = result.scalars().all()

        # Convert to JSON format
        fighters_data = []
        for fighter in fighters:
            fighters_data.append({
                "id": fighter.id,
                "name": fighter.name,
                "nickname": fighter.nickname,
                "division": fighter.division,
                "record": fighter.record,
                "stance": fighter.stance,
                "height": fighter.height,
                "weight": fighter.weight,
                "reach": fighter.reach,
            })

        # Write to file
        with output_file.open("w") as f:
            json.dump(fighters_data, f, indent=2)

        console.print(
            f"[green]✓[/green] Exported {len(fighters_data)} fighters to {output_file}"
        )


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Export active fighters to JSON")
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of fighters (for testing)",
    )
    args = parser.parse_args()

    await export_active_fighters(limit=args.limit)


if __name__ == "__main__":
    asyncio.run(main())
