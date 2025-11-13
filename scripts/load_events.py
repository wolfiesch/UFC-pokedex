#!/usr/bin/env python
"""Load scraped event data from JSON files into the PostgreSQL database."""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date as date_type
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import CacheClient, close_redis, get_cache_client
from backend.db.connection import get_session
from backend.db.models import Event
from backend.utils.event_utils import detect_event_type

# Load environment variables
load_dotenv()

console = Console()


def _parse_date(value: str | None) -> date_type | None:
    """Parse ISO date string to date object."""
    if not value:
        return None
    try:
        return date_type.fromisoformat(value)
    except (ValueError, AttributeError):
        return None


async def load_events_from_jsonl(
    session: AsyncSession,
    jsonl_path: Path,
    limit: int | None = None,
    dry_run: bool = False,
) -> int:
    """Load events from JSONL file."""
    if not jsonl_path.exists():
        console.print(f"[red]File not found: {jsonl_path}[/red]")
        return 0

    loaded_count = 0
    skipped_count = 0
    upcoming_count = 0
    completed_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading events from list...", total=None)

        with open(jsonl_path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                if limit and loaded_count >= limit:
                    break

                try:
                    data = json.loads(line.strip())

                    # Skip if not an event list item
                    if data.get("item_type") != "event_list":
                        continue

                    event_id = data.get("event_id")
                    if not event_id:
                        console.print(
                            f"[yellow]Line {line_num}: Missing event_id, skipping[/yellow]"
                        )
                        skipped_count += 1
                        continue

                    event_name = data.get("name", "Unknown Event")
                    event_date = _parse_date(data.get("date"))
                    status = data.get("status", "completed")

                    if not event_date:
                        console.print(
                            f"[yellow]Line {line_num}: Invalid date for event {event_name}, skipping[/yellow]"
                        )
                        skipped_count += 1
                        continue

                    if dry_run:
                        console.print(
                            f"[cyan]Would load event: {event_name} ({status})[/cyan]"
                        )
                        loaded_count += 1
                        if status == "upcoming":
                            upcoming_count += 1
                        else:
                            completed_count += 1
                        continue

                    # Create or update event
                    event = Event(
                        id=event_id,
                        name=event_name,
                        date=event_date,
                        location=data.get("location"),
                        status=status,
                        # Persist normalized classification so downstream queries can filter
                        # directly in SQL without recomputing detection heuristics.
                        event_type=detect_event_type(event_name).value,
                        venue=None,  # Will be populated from detail scraper
                        broadcast=None,  # Will be populated from detail scraper
                        promotion="UFC",
                        ufcstats_url=data.get("detail_url", ""),
                        tapology_url=None,  # Will be populated from Tapology scraper
                        sherdog_url=None,  # Will be populated from Tapology scraper
                    )

                    await session.merge(event)
                    loaded_count += 1

                    if status == "upcoming":
                        upcoming_count += 1
                    else:
                        completed_count += 1

                    # Commit every 50 events for progress visibility
                    if not dry_run and loaded_count % 50 == 0:
                        await session.commit()
                        progress.update(
                            task,
                            description=f"Loaded {loaded_count} events ({completed_count} completed, {upcoming_count} upcoming)...",
                        )

                except json.JSONDecodeError as e:
                    console.print(f"[red]Line {line_num}: JSON decode error: {e}[/red]")
                    skipped_count += 1
                except (ValueError, TypeError, KeyError) as e:
                    console.print(
                        f"[red]Line {line_num}: Error loading event: {e}[/red]"
                    )
                    if not dry_run and session.in_transaction():
                        await session.rollback()
                    skipped_count += 1

        if not dry_run and session.in_transaction():
            await session.commit()

    if skipped_count > 0:
        console.print(f"[yellow]Skipped {skipped_count} invalid events[/yellow]")

    console.print(
        f"\n[bold]Event breakdown:[/bold]\n"
        f"  • Completed events: {completed_count}\n"
        f"  • Upcoming events: {upcoming_count}\n"
        f"  • Total loaded: {loaded_count}"
    )

    return loaded_count


async def main(args: argparse.Namespace) -> None:
    """Main data loading function."""
    console.print("[bold blue]UFC Event Data Loader[/bold blue]\n")

    if args.dry_run:
        console.print(
            "[yellow]DRY RUN MODE - No data will be written to database[/yellow]\n"
        )

    cache_client: CacheClient | None = None
    if not args.dry_run:
        try:
            cache_client = await get_cache_client()
        except (ConnectionError, OSError, TimeoutError) as cache_error:
            console.print(
                f"[yellow]Warning: unable to connect to Redis cache ({cache_error}). Proceeding without caching.[/yellow]"
            )
            cache_client = None

    async with get_session() as session:
        # Load from events list
        list_path = Path("data/processed/events_list.jsonl")
        loaded_count = await load_events_from_jsonl(
            session, list_path, limit=args.limit, dry_run=args.dry_run
        )

        console.print(f"\n[green]✓ Loaded {loaded_count} events from list[/green]")

    if cache_client is not None and not args.dry_run:
        # Invalidate event cache keys
        try:
            # Clear any cached event lists
            keys_to_delete = []
            # Add patterns for event cache keys
            patterns = ["events:list:*", "events:detail:*"]
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
                console.print(
                    f"[dim]Invalidated {len(keys_to_delete)} cache entries[/dim]"
                )
        except (ConnectionError, OSError, TimeoutError) as e:
            console.print(f"[yellow]Warning: Could not invalidate cache: {e}[/yellow]")

        # Close Redis connection gracefully
        await close_redis()

    console.print("\n[bold green]Event data loading complete![/bold green]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load scraped event data into database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate data without inserting into database",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Only load first N events (for testing)",
    )

    args = parser.parse_args()

    asyncio.run(main(args))
