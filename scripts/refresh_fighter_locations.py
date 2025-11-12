"""
Refresh fighter location data with priority-based scheduling.

Usage:
    python scripts/refresh_fighter_locations.py --priority high --limit 100
    python scripts/refresh_fighter_locations.py --priority all --dry-run
    python scripts/refresh_fighter_locations.py --priority medium
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import click
import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import get_session
from backend.db.models import Fighter
from scripts.utils.gym_locations import resolve_gym_location


PriorityLevel = Literal["high", "medium", "low", "all"]
UFC_COM_BASE_URL = "https://www.ufc.com/athlete"
UFC_COM_HEADERS = {
    "User-Agent": "UFC-Pokedex-LocationRefresher/1.0 (+https://github.com/wolfgangschoenberger/ufc-pokedex)",
    "Accept-Language": "en-US,en;q=0.9",
}


def should_refresh_fighter(fighter: Fighter) -> bool:
    """
    Determine if a fighter's location data needs refreshing.

    Priority rules:
    - Never scraped: needs initial data
    - Active fighters: refresh every 30 days
    - Recent fighters (fought in last year): refresh every 90 days
    - All fighters: refresh if very stale (>180 days)
    - Skip if needs_manual_review flag set
    """
    # Never scraped - needs initial data
    if not fighter.ufc_com_scraped_at:
        return True

    # Skip if flagged for manual review
    if fighter.needs_manual_review:
        return False

    # Calculate staleness
    days_since_scrape = (datetime.utcnow() - fighter.ufc_com_scraped_at).days

    # Active fighters: refresh more frequently (30 days)
    # Note: We determine "active" by having fought in last 6 months
    if fighter.last_fight_date:
        days_since_fight = (datetime.utcnow().date() - fighter.last_fight_date).days
        if days_since_fight < 180 and days_since_scrape > 30:
            return True

    # Recent fighters: refresh quarterly (90 days)
    if fighter.last_fight_date:
        days_since_fight = (datetime.utcnow().date() - fighter.last_fight_date).days
        if days_since_fight < 365 and days_since_scrape > 90:
            return True

    # All fighters: refresh if very stale (180 days)
    if days_since_scrape > 180:
        return True

    return False


def determine_update_priority(fighter: Fighter) -> PriorityLevel:
    """
    Prioritize which fighters to update first.

    Returns:
        - "high": Active fighters with winning streak
        - "medium": Inactive but recent (fought in last year)
        - "low": Historical/retired fighters
    """
    # High priority: Active fighters with winning streak
    if (
        fighter.last_fight_date
        and fighter.current_streak_type == "win"
        and fighter.current_streak_count > 0
    ):
        days_since_fight = (datetime.utcnow().date() - fighter.last_fight_date).days
        if days_since_fight < 180:  # Fought in last 6 months
            return "high"

    # Medium priority: Recent but not necessarily active or on streak
    if fighter.last_fight_date:
        days_since_fight = (datetime.utcnow().date() - fighter.last_fight_date).days
        if days_since_fight < 365:  # Fought in last year
            return "medium"

    # Low priority: Historical/retired fighters
    return "low"


def detect_location_changes(old_fighter: Fighter, new_data: dict) -> dict:
    """
    Detect what changed between old and new data.

    Returns dict with:
        - has_changes: bool
        - birthplace_changed: bool
        - gym_changed: bool
        - changes_detail: list[dict]
    """
    changes = {
        "has_changes": False,
        "birthplace_changed": False,
        "gym_changed": False,
        "fighting_out_of_changed": False,
        "changes_detail": [],
    }

    # Check birthplace
    if old_fighter.birthplace != new_data.get("birthplace"):
        changes["has_changes"] = True
        changes["birthplace_changed"] = True
        changes["changes_detail"].append(
            {
                "field": "birthplace",
                "old": old_fighter.birthplace,
                "new": new_data.get("birthplace"),
            }
        )

    # Check training gym
    if old_fighter.training_gym != new_data.get("training_gym"):
        changes["has_changes"] = True
        changes["gym_changed"] = True
        changes["changes_detail"].append(
            {
                "field": "training_gym",
                "old": old_fighter.training_gym,
                "new": new_data.get("training_gym"),
            }
        )

    # Check fighting_out_of
    if old_fighter.fighting_out_of != new_data.get("fighting_out_of"):
        changes["has_changes"] = True
        changes["fighting_out_of_changed"] = True
        changes["changes_detail"].append(
            {
                "field": "fighting_out_of",
                "old": old_fighter.fighting_out_of,
                "new": new_data.get("fighting_out_of"),
            }
        )

    return changes


async def get_fighters_for_refresh(
    session: AsyncSession, priority: PriorityLevel, limit: int | None
) -> list[Fighter]:
    """
    Query fighters needing refresh based on priority level.
    """
    query = select(Fighter)

    # Filter by priority (if not "all")
    if priority != "all":
        # We'll filter in Python after loading since priority determination is complex
        query = query.order_by(Fighter.last_fight_date.desc().nullslast())
        if limit:
            # Load more than needed to account for filtering
            query = query.limit(limit * 3)

    result = await session.execute(query)
    all_fighters = result.scalars().all()

    # Filter by refresh criteria
    candidates = []
    for fighter in all_fighters:
        if not should_refresh_fighter(fighter):
            continue

        fighter_priority = determine_update_priority(fighter)

        # Skip if priority doesn't match
        if priority != "all" and fighter_priority != priority:
            continue

        candidates.append(fighter)

        # Stop if we have enough
        if limit and len(candidates) >= limit:
            break

    return candidates


def _parse_bio_fields(html: str) -> dict[str, str | None]:
    """Extract birthplace and training information from the UFC.com profile HTML."""

    soup = BeautifulSoup(html, "html.parser")
    bio_data: dict[str, str | None] = {}

    for field in soup.select(".c-bio__field"):
        label_el = field.select_one(".c-bio__label")
        value_el = field.select_one(".c-bio__text")
        if not label_el or not value_el:
            continue

        label = label_el.get_text(strip=True)
        value = value_el.get_text(strip=True)
        if not label or not value:
            continue

        if label.lower() == "place of birth":
            bio_data["birthplace"] = value
            if "," in value:
                city, country = value.split(",", 1)
                bio_data["birthplace_city"] = city.strip()
                bio_data["birthplace_country"] = country.strip()
            else:
                bio_data["birthplace_country"] = value
        elif label.lower() == "trains at":
            bio_data["training_gym"] = value

    return bio_data


async def refresh_fighter_data(
    fighter: Fighter,
    client: httpx.AsyncClient,
) -> dict | None:
    """Scrape UFC.com for updated fighter data."""

    if not fighter.ufc_com_slug:
        return None

    url = f"{UFC_COM_BASE_URL}/{fighter.ufc_com_slug}"
    response = await client.get(url, headers=UFC_COM_HEADERS, timeout=30.0)
    response.raise_for_status()

    parsed = _parse_bio_fields(response.text)
    if not parsed:
        return None

    gym_location = resolve_gym_location(parsed.get("training_gym"))
    if gym_location:
        if gym_location.city:
            parsed.setdefault("training_city", gym_location.city)
        if gym_location.country:
            parsed.setdefault("training_country", gym_location.country)

    return parsed


def write_change_log(fighter_id: str, fighter_name: str, changes: dict):
    """
    Write changes to JSONL log file.
    """
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.utcnow().date()
    log_file = log_dir / f"location_changes_{today.strftime('%Y-%m-%d')}.jsonl"

    for change in changes["changes_detail"]:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "fighter_id": fighter_id,
            "fighter_name": fighter_name,
            "change_type": f"{change['field']}_change",
            "field": change["field"],
            "old_value": change["old"],
            "new_value": change["new"],
            "source": "ufc.com",
            "confidence": 100.0,  # High confidence since it's from official source
        }

        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")


async def update_fighter_location(
    session: AsyncSession, fighter: Fighter, new_data: dict, dry_run: bool = False
) -> bool:
    """
    Update fighter location in database.

    Returns True if changes were made, False otherwise.
    """
    if dry_run:
        return False

    # Update fields
    if "birthplace" in new_data:
        fighter.birthplace = new_data["birthplace"]
    if "birthplace_city" in new_data:
        fighter.birthplace_city = new_data["birthplace_city"]
    if "birthplace_country" in new_data:
        fighter.birthplace_country = new_data["birthplace_country"]
    if "training_gym" in new_data:
        fighter.training_gym = new_data["training_gym"]
    if "training_city" in new_data:
        fighter.training_city = new_data["training_city"]
    if "training_country" in new_data:
        fighter.training_country = new_data["training_country"]
    if "fighting_out_of" in new_data:
        fighter.fighting_out_of = new_data["fighting_out_of"]

    # Update metadata
    fighter.ufc_com_scraped_at = datetime.utcnow()

    await session.commit()
    return True


@click.command()
@click.option(
    "--priority",
    type=click.Choice(["high", "medium", "low", "all"]),
    default="high",
    help="Priority level: high (active winners), medium (recent fighters), low (historical), all",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Max fighters to refresh in one run (default: no limit)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be refreshed without making changes",
)
def main(priority: PriorityLevel, limit: int | None, dry_run: bool):
    """
    Refresh fighter location data with priority-based scheduling.

    Examples:
        # Refresh top 100 high-priority fighters (daily)
        python scripts/refresh_fighter_locations.py --priority high --limit 100

        # Preview what would be refreshed
        python scripts/refresh_fighter_locations.py --priority medium --dry-run

        # Refresh all stale data (monthly)
        python scripts/refresh_fighter_locations.py --priority all
    """
    asyncio.run(run_refresh(priority, limit, dry_run))


async def run_refresh(priority: PriorityLevel, limit: int | None, dry_run: bool):
    """Main refresh logic."""
    stats = {
        "total_candidates": 0,
        "refreshed": 0,
        "changed": 0,
        "no_changes": 0,
        "errors": 0,
        "skipped_no_slug": 0,
    }

    click.echo(f"\n{'='*60}")
    click.echo(f"FIGHTER LOCATION REFRESH - Priority: {priority.upper()}")
    click.echo(f"{'='*60}\n")

    if dry_run:
        click.echo("🔍 DRY RUN MODE - No changes will be made\n")

    async with get_session() as session, httpx.AsyncClient() as http_client:
        # Get candidates for refresh
        click.echo(f"🔎 Finding fighters needing refresh (priority: {priority})...")
        candidates = await get_fighters_for_refresh(session, priority, limit)
        stats["total_candidates"] = len(candidates)

        if not candidates:
            click.echo("✅ No fighters need refreshing at this time")
            return

        click.echo(f"📋 Found {stats['total_candidates']} fighters to refresh\n")

        if dry_run:
            click.echo("Preview of fighters that would be refreshed:\n")

        # Process each fighter
        for i, fighter in enumerate(candidates, 1):
            # Skip if no UFC.com slug
            if not fighter.ufc_com_slug:
                stats["skipped_no_slug"] += 1
                if dry_run:
                    click.echo(
                        f"  [{i}/{stats['total_candidates']}] SKIP: {fighter.name} "
                        f"(no UFC.com slug)"
                    )
                continue

            # Calculate days since last scrape
            days_since_scrape = (
                (datetime.utcnow() - fighter.ufc_com_scraped_at).days
                if fighter.ufc_com_scraped_at
                else "never"
            )

            if dry_run:
                click.echo(
                    f"  [{i}/{stats['total_candidates']}] {fighter.name} "
                    f"(last scraped: {days_since_scrape} days ago, "
                    f"slug: {fighter.ufc_com_slug})"
                )
                continue

            try:
                # Fetch new data from UFC.com
                new_data = await refresh_fighter_data(fighter, http_client)

                if not new_data:
                    stats["no_changes"] += 1
                    continue

                # Detect changes
                changes = detect_location_changes(fighter, new_data)

                if changes["has_changes"]:
                    # Log changes
                    write_change_log(fighter.id, fighter.name, changes)

                    # Update database
                    await update_fighter_location(session, fighter, new_data, dry_run)

                    stats["changed"] += 1
                    click.echo(
                        f"✏️  [{i}/{stats['total_candidates']}] {fighter.name} - "
                        f"Updated: {', '.join([c['field'] for c in changes['changes_detail']])}"
                    )
                else:
                    stats["no_changes"] += 1

                stats["refreshed"] += 1

                # Commit every 10 fighters for safety
                if stats["refreshed"] % 10 == 0:
                    await session.commit()
                    click.echo(
                        f"💾 Progress: {stats['refreshed']}/{stats['total_candidates']} "
                        f"fighters processed"
                    )

            except Exception as e:
                stats["errors"] += 1
                click.echo(f"❌ Error refreshing {fighter.name}: {e}")

        # Final commit
        if not dry_run:
            await session.commit()

    # Print summary
    click.echo(f"\n{'='*60}")
    click.echo("SUMMARY")
    click.echo(f"{'='*60}")
    click.echo(f"Total candidates:        {stats['total_candidates']}")
    click.echo(f"Skipped (no slug):       {stats['skipped_no_slug']}")
    click.echo(f"Refreshed:               {stats['refreshed']}")
    click.echo(f"  - With changes:        {stats['changed']}")
    click.echo(f"  - No changes:          {stats['no_changes']}")
    click.echo(f"Errors:                  {stats['errors']}")
    click.echo(f"{'='*60}\n")

    if dry_run:
        click.echo(
            "ℹ️  This was a dry run. Run without --dry-run to apply changes.\n"
        )
    elif stats["changed"] > 0:
        today = datetime.utcnow().date()
        log_file = f"data/logs/location_changes_{today.strftime('%Y-%m-%d')}.jsonl"
        click.echo(f"📝 Changes logged to: {log_file}\n")


if __name__ == "__main__":
    main()
