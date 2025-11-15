#!/usr/bin/env python
"""Load scraped event detail data (fight cards) into the PostgreSQL database."""
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
from backend.db.models import Event, Fight

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


async def load_event_details_from_json(
    session: AsyncSession,
    json_dir: Path,
    limit: int | None = None,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Load event details from JSON files.

    Returns:
        Tuple of (events_loaded, fights_loaded)
    """
    if not json_dir.exists():
        console.print(f"[red]Directory not found: {json_dir}[/red]")
        return 0, 0

    json_files = sorted(json_dir.glob("*.json"))
    if not json_files:
        console.print(f"[red]No JSON files found in: {json_dir}[/red]")
        return 0, 0

    events_loaded = 0
    fights_loaded = 0
    skipped_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading event details...", total=len(json_files))

        for file_num, json_file in enumerate(json_files, 1):
            if limit and events_loaded >= limit:
                break

            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)

                event_id = data.get("event_id")
                if not event_id:
                    console.print(
                        f"[yellow]File {json_file.name}: Missing event_id, skipping[/yellow]"
                    )
                    skipped_count += 1
                    continue

                event_name = data.get("name", "Unknown Event")
                event_date = _parse_date(data.get("date"))
                status = data.get("status", "completed")
                fight_card = data.get("fight_card", [])

                if not event_date:
                    console.print(
                        f"[yellow]File {json_file.name}: Invalid date for event {event_name}, skipping[/yellow]"
                    )
                    skipped_count += 1
                    continue

                if dry_run:
                    console.print(
                        f"[cyan]Would load event: {event_name} with {len(fight_card)} fights[/cyan]"
                    )
                    events_loaded += 1
                    fights_loaded += len(fight_card)
                    progress.advance(task)
                    continue

                # Update event with additional details
                event = Event(
                    id=event_id,
                    name=event_name,
                    date=event_date,
                    location=data.get("location"),
                    status=status,
                    venue=data.get("venue"),
                    broadcast=data.get("broadcast"),
                    promotion=data.get("promotion", "UFC"),
                    ufcstats_url=data.get("detail_url", ""),
                    tapology_url=data.get("tapology_url"),
                    sherdog_url=data.get("sherdog_url"),
                )
                await session.merge(event)
                events_loaded += 1

                # Load fights from fight card
                for fight_data in fight_card:
                    fight_id = fight_data.get("fight_id")
                    if not fight_id:
                        continue

                    # Determine result based on event status and date
                    # Check if event is upcoming (either by status or date)
                    is_upcoming = status == "upcoming" or (
                        event_date and event_date > date_type.today()
                    )

                    # Set result to "next" for upcoming fights, otherwise check fight data
                    result = fight_data.get("result")
                    if is_upcoming and not result:
                        result = "next"

                    weight_class = fight_data.get("weight_class")
                    method = fight_data.get("method")
                    fight_round = fight_data.get("round")
                    fight_time = fight_data.get("time")
                    fight_url = fight_data.get("fight_url")
                    fighter_one_id = fight_data.get("fighter_1_id") or "unknown"
                    fighter_two_id = fight_data.get("fighter_2_id")

                    fight = Fight(
                        id=fight_id,
                        fighter_id=fighter_one_id,
                        event_id=event_id,
                        opponent_id=fighter_two_id,
                        opponent_name=fight_data.get("fighter_2_name", "Unknown"),
                        event_name=event_name,
                        event_date=event_date,
                        result=result or "N/A",
                        method=method,
                        round=fight_round,
                        time=fight_time,
                        fight_card_url=fight_url,
                        weight_class=weight_class,
                    )
                    await session.merge(fight)
                    fights_loaded += 1

                    # For upcoming fights, capture the fighter_2 perspective so both fighters
                    # get downstream "next fight" metadata (important for roster cards).
                    if is_upcoming and fighter_two_id:
                        mirrored_fight = Fight(
                            # Synthetic ID ensures we do not collide with canonical UFCStats identifiers.
                            id=f"{fight_id}-opp",
                            fighter_id=fighter_two_id,
                            event_id=event_id,
                            opponent_id=fighter_one_id,
                            opponent_name=fight_data.get("fighter_1_name", "Unknown"),
                            event_name=event_name,
                            event_date=event_date,
                            result=result or "N/A",
                            method=method,
                            round=fight_round,
                            time=fight_time,
                            fight_card_url=fight_url,
                            weight_class=weight_class,
                        )
                        await session.merge(mirrored_fight)
                        fights_loaded += 1

                # Commit every 50 events for progress visibility
                if not dry_run and events_loaded % 50 == 0:
                    await session.commit()
                    progress.update(
                        task,
                        description=f"Loaded {events_loaded} events, {fights_loaded} fights...",
                    )

                progress.advance(task)

            except json.JSONDecodeError as e:
                console.print(f"[red]File {json_file.name}: JSON decode error: {e}[/red]")
                skipped_count += 1
            except (ValueError, TypeError, KeyError) as e:
                console.print(
                    f"[red]File {json_file.name}: Error loading event: {e}[/red]"
                )
                if not dry_run and session.in_transaction():
                    await session.rollback()
                skipped_count += 1

        if not dry_run and session.in_transaction():
            await session.commit()

    if skipped_count > 0:
        console.print(f"[yellow]Skipped {skipped_count} invalid events[/yellow]")

    return events_loaded, fights_loaded


async def main(args: argparse.Namespace) -> None:
    """Main data loading function."""
    console.print("[bold blue]UFC Event Details Data Loader[/bold blue]\n")

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
        # Load from event detail JSON files
        json_dir = Path("data/processed/events")
        events_loaded, fights_loaded = await load_event_details_from_json(
            session, json_dir, limit=args.limit, dry_run=args.dry_run
        )

        console.print(
            f"\n[green]✓ Loaded {events_loaded} events with {fights_loaded} fights[/green]"
        )

    if cache_client is not None and not args.dry_run:
        # Invalidate event and fighter cache keys
        try:
            keys_to_delete = []
            patterns = ["events:*", "fighters:*"]
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

    console.print("\n[bold green]Event details loading complete![/bold green]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load scraped event detail data into database"
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
