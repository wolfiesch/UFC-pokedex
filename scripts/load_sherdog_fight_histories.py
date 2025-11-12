#!/usr/bin/env python3
"""Load Sherdog fight histories into the database.

This script reads the sherdog_fight_histories.jsonl file and:
1. Creates or updates fighter records with Sherdog data
2. Inserts all fight records
3. Updates fighter statistics (primary_promotion, total_fights, etc.)

Usage:
    python scripts/load_sherdog_fight_histories.py [--dry-run] [--limit N]
"""

import asyncio
import json
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import click
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from backend.db.connection import get_session
from backend.db.models import Fighter, Fight


async def load_or_create_fighter(
    session,
    fighter_data: dict[str, Any],
    dry_run: bool = False,
) -> str | None:
    """Load or create a fighter record.

    Args:
        session: Database session
        fighter_data: Fighter data from Sherdog scrape
        dry_run: If True, don't commit changes

    Returns:
        Fighter ID or None if dry run
    """
    sherdog_id = fighter_data["sherdog_id"]
    fighter_name = fighter_data["fighter_name"]
    sherdog_url = fighter_data["sherdog_url"]

    # Check if fighter already exists by Sherdog ID
    result = await session.execute(
        select(Fighter).where(Fighter.sherdog_id == sherdog_id)
    )
    existing_fighter = result.scalar_one_or_none()

    if existing_fighter:
        click.echo(f"  📝 Updating existing fighter: {fighter_name} (ID: {existing_fighter.id})")

        # Update Sherdog data
        existing_fighter.sherdog_id = sherdog_id
        existing_fighter.sherdog_url = sherdog_url
        existing_fighter.total_fights = fighter_data["total_fights"]

        # Update promotion data
        if fighter_data.get("promotions"):
            existing_fighter.all_promotions = fighter_data["promotions"]
            # Set primary promotion as the one with most fights
            primary_promo = max(fighter_data["promotions"].items(), key=lambda x: x[1])[0]
            existing_fighter.primary_promotion = primary_promo

        # Update record if available
        if fighter_data.get("record"):
            record = fighter_data["record"]
            record_str = record.get("record_string")
            if record_str:
                existing_fighter.record = record_str

        if not dry_run:
            await session.flush()

        return existing_fighter.id

    else:
        # Create new fighter
        click.echo(f"  ➕ Creating new fighter: {fighter_name}")

        fighter_id = str(uuid.uuid4())[:16]  # Generate short UUID

        # Prepare promotion data
        promotions = fighter_data.get("promotions", {})
        primary_promo = None
        if promotions:
            primary_promo = max(promotions.items(), key=lambda x: x[1])[0]

        # Prepare record
        record_str = None
        if fighter_data.get("record"):
            record_str = fighter_data["record"].get("record_string")

        # Create fighter object
        new_fighter = Fighter(
            id=fighter_id,
            name=fighter_name,
            sherdog_id=sherdog_id,
            sherdog_url=sherdog_url,
            record=record_str,
            total_fights=fighter_data["total_fights"],
            primary_promotion=primary_promo,
            all_promotions=promotions,
            division=fighter_data.get("division"),
        )

        session.add(new_fighter)

        if not dry_run:
            await session.flush()

        return fighter_id


async def load_fights(
    session,
    fighter_id: str,
    sherdog_id: int,
    fights: list[dict[str, Any]],
    dry_run: bool = False,
) -> int:
    """Load fight records for a fighter.

    Args:
        session: Database session
        fighter_id: Fighter's database ID
        sherdog_id: Fighter's Sherdog ID
        fights: List of fight records
        dry_run: If True, don't commit changes

    Returns:
        Number of fights loaded
    """
    loaded_count = 0

    for fight in fights:
        # Skip fights with missing critical data
        if not fight.get("opponent_name") or not fight.get("event_name"):
            click.echo(f"    ⚠️  Skipping fight with missing data: {fight}")
            continue

        # Generate fight ID (could use event_date + opponent_name for uniqueness)
        fight_id = str(uuid.uuid4())[:16]

        # Parse event date
        event_date = None
        if fight.get("event_date"):
            try:
                event_date = datetime.strptime(fight["event_date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass

        # Create fight object
        new_fight = Fight(
            id=fight_id,
            fighter_id=fighter_id,
            opponent_name=fight["opponent_name"],
            opponent_sherdog_id=fight.get("opponent_sherdog_id"),
            event_name=fight["event_name"],
            event_sherdog_id=fight.get("event_sherdog_id"),
            event_date=event_date,
            result=fight["result"],
            method=fight.get("method"),
            method_details=fight.get("method_details"),
            round=fight.get("round"),
            time=fight.get("time"),
            promotion=fight.get("promotion"),
            is_amateur=False,  # Sherdog only shows pro fights by default
        )

        session.add(new_fight)
        loaded_count += 1

    if not dry_run and loaded_count > 0:
        await session.flush()

    return loaded_count


async def process_fight_histories(
    input_file: Path,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    """Process all fight histories from JSONL file.

    Args:
        input_file: Path to sherdog_fight_histories.jsonl
        dry_run: If True, don't commit changes
        limit: Maximum number of fighters to process

    Returns:
        Statistics dict
    """
    stats = {
        "fighters_processed": 0,
        "fighters_created": 0,
        "fighters_updated": 0,
        "fights_loaded": 0,
        "errors": [],
    }

    click.echo(f"\n{'=' * 60}")
    click.echo("LOADING SHERDOG FIGHT HISTORIES")
    click.echo(f"{'=' * 60}\n")

    if dry_run:
        click.echo("🔍 DRY RUN MODE - No database changes will be made\n")

    async with get_session() as session:
        with input_file.open() as f:
            for line_num, line in enumerate(f, 1):
                if limit and line_num > limit:
                    break

                try:
                    fighter_data = json.loads(line)

                    click.echo(f"[{line_num}] Processing {fighter_data['fighter_name']}...")

                    # Load or create fighter
                    fighter_id = await load_or_create_fighter(session, fighter_data, dry_run)

                    if fighter_id:
                        # Check if this is new or updated
                        result = await session.execute(
                            select(Fighter).where(Fighter.id == fighter_id)
                        )
                        fighter = result.scalar_one_or_none()

                        if fighter:
                            # Count as created or updated based on whether record existed
                            # (This is approximate - we could track more precisely)
                            stats["fighters_updated"] += 1
                        else:
                            stats["fighters_created"] += 1

                        # Load fights
                        fights = fighter_data.get("fights", [])
                        if fights:
                            num_fights = await load_fights(
                                session,
                                fighter_id,
                                fighter_data["sherdog_id"],
                                fights,
                                dry_run,
                            )
                            stats["fights_loaded"] += num_fights
                            click.echo(f"  ✅ Loaded {num_fights} fights")

                    stats["fighters_processed"] += 1

                except Exception as e:
                    error_msg = f"Line {line_num}: {str(e)}"
                    stats["errors"].append(error_msg)
                    click.echo(f"  ❌ Error: {e}", err=True)
                    continue

        if not dry_run:
            await session.commit()
            click.echo("\n✅ Changes committed to database")
        else:
            click.echo("\n🔍 Dry run complete - no changes made")

    return stats


@click.command()
@click.option(
    "--input-file",
    type=click.Path(exists=True, path_type=Path),
    default=Path("data/processed/sherdog_fight_histories.jsonl"),
    help="Path to sherdog_fight_histories.jsonl file",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Run without committing to database",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit number of fighters to process (for testing)",
)
def main(input_file: Path, dry_run: bool, limit: int | None):
    """Load Sherdog fight histories into the database."""
    if not input_file.exists():
        click.echo(f"❌ Input file not found: {input_file}", err=True)
        click.echo("Run: scrapy crawl sherdog_fight_history first", err=True)
        return 1

    # Count lines in file
    with input_file.open() as f:
        total_fighters = sum(1 for _ in f)

    click.echo(f"📂 Input file: {input_file}")
    click.echo(f"📊 Total fighters in file: {total_fighters}")
    if limit:
        click.echo(f"🔢 Processing limit: {limit}")
    click.echo()

    # Run async processing
    stats = asyncio.run(process_fight_histories(input_file, dry_run, limit))

    # Print summary
    click.echo(f"\n{'=' * 60}")
    click.echo("SUMMARY")
    click.echo(f"{'=' * 60}")
    click.echo(f"Fighters processed:  {stats['fighters_processed']}")
    click.echo(f"Fighters created:    {stats['fighters_created']}")
    click.echo(f"Fighters updated:    {stats['fighters_updated']}")
    click.echo(f"Fights loaded:       {stats['fights_loaded']}")
    click.echo(f"Errors:              {len(stats['errors'])}")

    if stats["errors"]:
        click.echo("\n❌ Errors encountered:")
        for error in stats["errors"][:10]:  # Show first 10 errors
            click.echo(f"  - {error}")
        if len(stats["errors"]) > 10:
            click.echo(f"  ... and {len(stats['errors']) - 10} more")

    click.echo(f"\n{'=' * 60}")

    if dry_run:
        click.echo("\n🔍 This was a dry run. Run without --dry-run to apply changes.")
    else:
        click.echo(f"\n✅ Successfully loaded {stats['fights_loaded']} fights for {stats['fighters_processed']} fighters!")

    return 0 if not stats["errors"] else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
