#!/usr/bin/env python
"""Migrate fights with result='N/A' to result='next' for upcoming events."""
from __future__ import annotations

import argparse
import asyncio
from datetime import date

from dotenv import load_dotenv
from rich.console import Console
from sqlalchemy import select, update

from backend.db.connection import get_session
from backend.db.models import Fight

load_dotenv()

console = Console()


async def migrate_na_fights(dry_run: bool = False) -> None:
    """
    Migrate fights with result='N/A' to result='next' for upcoming events.

    Args:
        dry_run: If True, only preview changes without applying them
    """
    console.print("[bold blue]UFC Fight Migration: N/A → next[/bold blue]\n")

    today = date.today()

    async with get_session() as session:
        # Query all fights with result='N/A'
        query = select(Fight).where(Fight.result == "N/A")
        result = await session.execute(query)
        na_fights = result.scalars().all()

        if not na_fights:
            console.print("[yellow]No fights with result='N/A' found.[/yellow]")
            return

        console.print(f"Found [cyan]{len(na_fights)}[/cyan] fights with result='N/A'\n")

        # Separate upcoming from past/unknown
        upcoming_fights = []
        past_or_unknown = []

        for fight in na_fights:
            if fight.event_date and fight.event_date > today:
                upcoming_fights.append(fight)
            else:
                past_or_unknown.append(fight)

        console.print(f"  → [green]{len(upcoming_fights)}[/green] upcoming fights (will be updated to 'next')")
        console.print(f"  → [yellow]{len(past_or_unknown)}[/yellow] past/unknown date fights (will remain 'N/A')\n")

        if not upcoming_fights:
            console.print("[yellow]No upcoming fights to migrate.[/yellow]")
            return

        # Show sample of fights to be updated
        if upcoming_fights:
            console.print("[bold]Sample upcoming fights to migrate:[/bold]")
            for fight in upcoming_fights[:5]:
                console.print(
                    f"  • {fight.event_name} ({fight.event_date}): "
                    f"{fight.opponent_name} - result: [red]N/A[/red] → [green]next[/green]"
                )
            if len(upcoming_fights) > 5:
                console.print(f"  ... and {len(upcoming_fights) - 5} more")
            console.print()

        if dry_run:
            console.print("[bold yellow]DRY RUN MODE - No changes applied[/bold yellow]")
            return

        # Update upcoming fights to result='next'
        console.print("[cyan]Applying migration...[/cyan]")

        # Bulk update for performance
        upcoming_ids = [fight.id for fight in upcoming_fights]
        await session.execute(
            update(Fight)
            .where(Fight.id.in_(upcoming_ids))
            .values(result="next")
        )

        await session.commit()

        console.print(f"[bold green]✓ Successfully migrated {len(upcoming_fights)} fights![/bold green]")
        console.print("\n[dim]Fights with past/unknown dates remain as 'N/A' (may indicate missing data)[/dim]")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate fights with result='N/A' to result='next' for upcoming events"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them",
    )
    args = parser.parse_args()

    await migrate_na_fights(dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
