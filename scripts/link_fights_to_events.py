#!/usr/bin/env python
"""Link existing fight records to events by matching event names."""
from __future__ import annotations

import argparse
import asyncio

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import close_redis, get_cache_client
from backend.db.connection import get_session
from backend.db.models import Event, Fight

# Load environment variables
load_dotenv()

console = Console()


def normalize_event_name(name: str) -> str:
    """Normalize event name for matching (lowercase, strip whitespace)."""
    return name.lower().strip()


async def link_fights_to_events(
    session: AsyncSession,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Link fights to events by matching event names.

    Returns:
        Tuple of (matched_count, unmatched_count)
    """
    # Load all events and create a mapping
    console.print("[bold blue]Loading events from database...[/bold blue]")
    result = await session.execute(select(Event))
    events = result.scalars().all()

    # Create normalized name -> event mapping
    event_map: dict[str, Event] = {}
    for event in events:
        normalized_name = normalize_event_name(event.name)
        event_map[normalized_name] = event

    console.print(f"[green]✓ Loaded {len(events)} events[/green]\n")

    # Load all fights without event_id
    console.print("[bold blue]Loading unlinked fights...[/bold blue]")
    result = await session.execute(
        select(Fight).where(Fight.event_id.is_(None))
    )
    unlinked_fights = result.scalars().all()

    console.print(f"[yellow]Found {len(unlinked_fights)} fights without event_id[/yellow]\n")

    if not unlinked_fights:
        console.print("[green]✓ All fights are already linked to events![/green]")
        return 0, 0

    matched_count = 0
    unmatched_count = 0
    unmatched_events = set()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Linking fights to events...", total=len(unlinked_fights))

        for fight in unlinked_fights:
            normalized_name = normalize_event_name(fight.event_name)
            matched_event = event_map.get(normalized_name)

            if matched_event:
                if dry_run:
                    console.print(
                        f"[cyan]Would link: {fight.fighter_id[:8]} → {matched_event.name}[/cyan]"
                    )
                else:
                    fight.event_id = matched_event.id
                matched_count += 1
            else:
                unmatched_count += 1
                unmatched_events.add(fight.event_name)

            progress.advance(task)

            # Commit in batches for performance
            if not dry_run and matched_count % 100 == 0:
                await session.commit()
                progress.update(
                    task,
                    description=f"Linked {matched_count} fights ({unmatched_count} unmatched)...",
                )

    # Final commit
    if not dry_run and session.in_transaction():
        await session.commit()

    # Report unmatched events (if any)
    if unmatched_events:
        console.print(f"\n[yellow]⚠ {len(unmatched_events)} unique event names could not be matched:[/yellow]")
        for event_name in sorted(unmatched_events)[:10]:  # Show first 10
            console.print(f"  • {event_name}")
        if len(unmatched_events) > 10:
            console.print(f"  ... and {len(unmatched_events) - 10} more")

    return matched_count, unmatched_count


async def main(args: argparse.Namespace) -> None:
    """Main function."""
    console.print("[bold blue]UFC Fight-Event Linker[/bold blue]\n")

    if args.dry_run:
        console.print("[yellow]DRY RUN MODE - No data will be written[/yellow]\n")

    async with get_session() as session:
        matched, unmatched = await link_fights_to_events(session, dry_run=args.dry_run)

        console.print("\n[bold]Results:[/bold]")
        console.print(f"  • Matched: [green]{matched}[/green]")
        console.print(f"  • Unmatched: [yellow]{unmatched}[/yellow]")
        console.print(f"  • Success rate: [cyan]{matched / (matched + unmatched) * 100:.1f}%[/cyan]")

    # Invalidate cache if we made changes
    if not args.dry_run and matched > 0:
        try:
            cache_client = await get_cache_client()
            if cache_client:
                # Clear fighter and event caches since relationships changed
                patterns = ["fighters:*", "events:*"]
                keys_to_delete = []
                for pattern in patterns:
                    cursor = 0
                    while True:
                        cursor, keys = await cache_client._redis.scan(
                            cursor, match=pattern, count=100
                        )
                        keys_to_delete.extend(keys)
                        if cursor == 0:
                            break

                if keys_to_delete:
                    await cache_client._redis.delete(*keys_to_delete)
                    console.print(f"\n[dim]Invalidated {len(keys_to_delete)} cache entries[/dim]")

                await close_redis()
        except (ConnectionError, OSError, TimeoutError) as e:
            console.print(f"\n[yellow]Warning: Could not invalidate cache: {e}[/yellow]")

    console.print("\n[bold green]✓ Fight-event linking complete![/bold green]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Link existing fights to events by matching event names"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be linked without making changes",
    )

    args = parser.parse_args()
    asyncio.run(main(args))
