#!/usr/bin/env python
"""Load scraped fighter data from JSON files into the PostgreSQL database."""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import get_session
from backend.db.models import Fight, Fighter

# Load environment variables
load_dotenv()

console = Console()


def _parse_date(value: Any) -> date | None:
    """Convert ISO strings to date objects expected by SQLAlchemy models."""
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return date.fromisoformat(text)
        except ValueError:
            console.print(f"[yellow]Unable to parse date '{value}', storing as NULL[/yellow]")
            return None
    console.print(f"[yellow]Unexpected date value type {type(value)!r}; storing as NULL[/yellow]")
    return None


async def load_fighters_from_jsonl(
    session: AsyncSession,
    jsonl_path: Path,
    limit: int | None = None,
    dry_run: bool = False,
) -> int:
    """Load fighters from JSONL file."""
    if not jsonl_path.exists():
        console.print(f"[red]File not found: {jsonl_path}[/red]")
        return 0

    loaded_count = 0
    skipped_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading fighters from list...", total=None)

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                if limit and loaded_count >= limit:
                    break

                try:
                    data = json.loads(line.strip())

                    # Skip if not a fighter list item
                    if data.get("item_type") != "fighter_list":
                        continue

                    fighter_id = data.get("fighter_id")
                    if not fighter_id:
                        console.print(
                            f"[yellow]Line {line_num}: Missing fighter_id, skipping[/yellow]"
                        )
                        skipped_count += 1
                        continue

                    if dry_run:
                        console.print(f"[cyan]Would load fighter: {data.get('name')}[/cyan]")
                        loaded_count += 1
                        continue

                    # Create or update fighter
                    fighter = Fighter(
                        id=fighter_id,
                        name=data.get("name", "Unknown"),
                        nickname=data.get("nickname"),
                        height=data.get("height"),
                        weight=data.get("weight"),
                        reach=data.get("reach"),
                        stance=data.get("stance"),
                        dob=_parse_date(data.get("dob")),
                        division=None,  # Not in list data
                        leg_reach=None,  # Not in list data
                        record=None,  # Not in list data
                    )

                    await session.merge(fighter)
                    loaded_count += 1

                    if not dry_run:
                        await session.commit()

                except json.JSONDecodeError as e:
                    console.print(f"[red]Line {line_num}: JSON decode error: {e}[/red]")
                    skipped_count += 1
                except Exception as e:
                    console.print(f"[red]Line {line_num}: Error loading fighter: {e}[/red]")
                    if not dry_run and session.in_transaction():
                        await session.rollback()
                    skipped_count += 1

        if not dry_run and session.in_transaction():
            await session.commit()

    return loaded_count


async def load_fighter_detail(
    session: AsyncSession,
    json_path: Path,
    dry_run: bool = False,
) -> bool:
    """Load detailed fighter data from individual JSON file."""
    if not json_path.exists():
        console.print(f"[red]File not found: {json_path}[/red]")
        return False

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        fighter_id = data.get("fighter_id")
        if not fighter_id:
            console.print(f"[yellow]Missing fighter_id in {json_path}[/yellow]")
            return False

        if dry_run:
            console.print(f"[cyan]Would load detailed data for: {data.get('name')}[/cyan]")
            return True

        # Update fighter with detailed data
        fighter = await session.get(Fighter, fighter_id)
        if not fighter:
            # Create new fighter if doesn't exist
            fighter = Fighter(id=fighter_id)
            session.add(fighter)

        # Update fighter fields
        fighter.name = data.get("name", fighter.name)
        fighter.nickname = data.get("nickname")
        fighter.height = data.get("height")
        fighter.weight = data.get("weight")
        fighter.reach = data.get("reach")
        fighter.leg_reach = data.get("leg_reach")
        fighter.stance = data.get("stance")
        fighter.dob = _parse_date(data.get("dob"))
        fighter.division = data.get("division")
        fighter.record = data.get("record")

        # Load fight history
        fight_history = data.get("fight_history", [])
        for fight_data in fight_history:
            fight_id = fight_data.get("fight_id")
            if not fight_id:
                continue

            # Check if fight already exists
            existing_fight = await session.get(Fight, fight_id)
            if existing_fight:
                continue  # Skip if already loaded

            fight = Fight(
                id=fight_id,
                fighter_id=fighter_id,
                opponent_id=fight_data.get("opponent_id"),
                opponent_name=fight_data.get("opponent") or "Unknown",
                event_name=fight_data.get("event_name") or "Unknown Event",
                event_date=_parse_date(fight_data.get("event_date")),
                result=fight_data.get("result") or "Unknown",
                method=fight_data.get("method"),
                round=fight_data.get("round"),
                time=fight_data.get("time"),
                fight_card_url=fight_data.get("fight_card_url"),
            )
            session.add(fight)

        await session.commit()
        return True

    except Exception as e:
        console.print(f"[red]Error loading {json_path}: {e}[/red]")
        if session.in_transaction():
            await session.rollback()
        return False


async def main(args: argparse.Namespace) -> None:
    """Main data loading function."""
    console.print("[bold blue]UFC Fighter Data Loader[/bold blue]\n")

    if args.dry_run:
        console.print("[yellow]DRY RUN MODE - No data will be written to database[/yellow]\n")

    async with get_session() as session:
        if args.fighter_id:
            # Load specific fighter detail
            detail_path = Path(f"data/processed/fighters/{args.fighter_id}.json")
            success = await load_fighter_detail(session, detail_path, dry_run=args.dry_run)
            if success:
                console.print(f"[green]✓ Loaded fighter {args.fighter_id}[/green]")
            else:
                console.print(f"[red]✗ Failed to load fighter {args.fighter_id}[/red]")

        else:
            # Load from fighters list
            list_path = Path("data/processed/fighters_list.jsonl")
            loaded_count = await load_fighters_from_jsonl(
                session, list_path, limit=args.limit, dry_run=args.dry_run
            )

            console.print(f"\n[green]✓ Loaded {loaded_count} fighters from list[/green]")

            # Optionally load detailed data for all fighters
            if args.load_details:
                fighters_dir = Path("data/processed/fighters")
                if fighters_dir.exists():
                    fighter_files = list(fighters_dir.glob("*.json"))
                    console.print(f"\n[blue]Loading detailed data for {len(fighter_files)} fighters...[/blue]")

                    success_count = 0
                    for fighter_file in fighter_files:
                        if args.limit and success_count >= args.limit:
                            break

                        success = await load_fighter_detail(session, fighter_file, dry_run=args.dry_run)
                        if success:
                            success_count += 1

                    console.print(f"[green]✓ Loaded detailed data for {success_count} fighters[/green]")

    console.print("\n[bold green]Data loading complete![/bold green]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load scraped fighter data into database")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate data without inserting into database",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Only load first N fighters (for testing)",
    )
    parser.add_argument(
        "--fighter-id",
        type=str,
        help="Load specific fighter by ID",
    )
    parser.add_argument(
        "--load-details",
        action="store_true",
        help="Load detailed fighter data from individual JSON files",
    )

    args = parser.parse_args()

    asyncio.run(main(args))
