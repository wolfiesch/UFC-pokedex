#!/usr/bin/env python
"""Load scraped fighter data from JSON files into the PostgreSQL database."""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import get_session
from backend.db.models import Fight, Fighter, fighter_stats

# Load environment variables
load_dotenv()

console = Console()


LANDED_ATTEMPT_RE = re.compile(r"(?P<landed>\d+)\s*(?:of|/)\s*(?P<attempted>\d+)", re.IGNORECASE)
PERCENT_RE = re.compile(r"(?P<pct>\d+(?:\.\d+)?)%")


def _parse_landed_attempted(value: Any) -> tuple[int, int] | None:
    """Parse strings like '30 of 75' into landed/attempted totals."""
    if value in (None, "", "--"):
        return None
    text = str(value).strip()
    if not text or text == "--":
        return None
    text = text.replace(",", "")
    match = LANDED_ATTEMPT_RE.search(text)
    if not match:
        return None
    return int(match.group("landed")), int(match.group("attempted"))


def _parse_percentage(value: Any) -> float | None:
    """Parse percentage strings like '45%' into a ratio between 0 and 1."""
    if value in (None, "", "--"):
        return None
    text = str(value).strip()
    if not text:
        return None
    percent_match = PERCENT_RE.search(text)
    if percent_match:
        return float(percent_match.group("pct")) / 100.0
    try:
        numeric = float(text)
    except ValueError:
        return None
    # Handle both 0-1 and 0-100 scale values
    return numeric / 100.0 if numeric > 1 else numeric


def _format_number(value: float, decimals: int = 2) -> str:
    """Format floats with trailing zeros trimmed."""
    formatted = f"{value:.{decimals}f}"
    return formatted.rstrip("0").rstrip(".")


def _format_percentage(value: float, decimals: int = 1) -> str:
    """Format a ratio as a percentage string."""
    percent = value * 100
    formatted = f"{percent:.{decimals}f}"
    return f"{formatted.rstrip('0').rstrip('.')}%"


def _average(total: float, count: int) -> float | None:
    if count <= 0:
        return None
    return total / count


def _compute_accuracy(
    landed_total: int,
    attempted_total: int,
    pct_sum: float,
    pct_count: int,
) -> float | None:
    """Compute accuracy using totals, falling back to averaged percentages."""
    if attempted_total > 0:
        return landed_total / attempted_total
    if pct_count > 0:
        return pct_sum / pct_count
    return None


def calculate_fighter_stats(fight_history: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """Aggregate per-fight stats into career averages."""
    sig_totals = {"landed": 0, "attempted": 0, "count": 0, "pct_sum": 0.0, "pct_count": 0}
    total_totals = {"landed": 0, "attempted": 0, "count": 0}
    td_totals = {"completed": 0, "attempted": 0, "count": 0}

    for fight in fight_history or []:
        stats = fight.get("stats") or {}

        sig_pair = _parse_landed_attempted(stats.get("sig_strikes"))
        if sig_pair:
            sig_totals["landed"] += sig_pair[0]
            sig_totals["attempted"] += sig_pair[1]
            sig_totals["count"] += 1

        sig_pct = _parse_percentage(stats.get("sig_strikes_pct"))
        if sig_pct is not None:
            sig_totals["pct_sum"] += sig_pct
            sig_totals["pct_count"] += 1

        total_pair = _parse_landed_attempted(stats.get("total_strikes"))
        if total_pair:
            total_totals["landed"] += total_pair[0]
            total_totals["attempted"] += total_pair[1]
            total_totals["count"] += 1

        td_pair = _parse_landed_attempted(stats.get("takedowns"))
        if td_pair:
            td_totals["completed"] += td_pair[0]
            td_totals["attempted"] += td_pair[1]
            td_totals["count"] += 1

    results: dict[str, dict[str, str]] = {}

    avg_sig_landed = _average(sig_totals["landed"], sig_totals["count"])
    avg_sig_attempted = _average(sig_totals["attempted"], sig_totals["count"])
    sig_accuracy = _compute_accuracy(
        sig_totals["landed"],
        sig_totals["attempted"],
        sig_totals["pct_sum"],
        sig_totals["pct_count"],
    )
    if any(value is not None for value in (avg_sig_landed, avg_sig_attempted, sig_accuracy)):
        category = {}
        if avg_sig_landed is not None:
            category["avg_landed"] = _format_number(avg_sig_landed)
        if avg_sig_attempted is not None:
            category["avg_attempted"] = _format_number(avg_sig_attempted)
        if sig_accuracy is not None:
            category["accuracy_pct"] = _format_percentage(sig_accuracy)
        if category:
            results["significant_strikes"] = category

    avg_total_landed = _average(total_totals["landed"], total_totals["count"])
    avg_total_attempted = _average(total_totals["attempted"], total_totals["count"])
    total_accuracy = None
    if total_totals["attempted"] > 0:
        total_accuracy = total_totals["landed"] / total_totals["attempted"]
    if any(value is not None for value in (avg_total_landed, avg_total_attempted, total_accuracy)):
        category = {}
        if avg_total_landed is not None:
            category["total_strikes_landed_avg"] = _format_number(avg_total_landed)
        if avg_total_attempted is not None:
            category["total_strikes_attempted_avg"] = _format_number(avg_total_attempted)
        if total_accuracy is not None:
            category["total_strikes_accuracy_pct"] = _format_percentage(total_accuracy)
        if category:
            results["striking"] = category

    avg_td_completed = _average(td_totals["completed"], td_totals["count"])
    avg_td_attempted = _average(td_totals["attempted"], td_totals["count"])
    td_accuracy = None
    if td_totals["attempted"] > 0:
        td_accuracy = td_totals["completed"] / td_totals["attempted"]
    if any(value is not None for value in (avg_td_completed, avg_td_attempted, td_accuracy)):
        td_category = {}
        if avg_td_completed is not None:
            td_category["takedowns_completed_avg"] = _format_number(avg_td_completed)
        if avg_td_attempted is not None:
            td_category["takedowns_attempted_avg"] = _format_number(avg_td_attempted)
        if td_accuracy is not None:
            td_category["takedown_accuracy_pct"] = _format_percentage(td_accuracy)
        if td_category:
            results["takedown_stats"] = td_category
            grappling_metrics: dict[str, str] = {}
            if "takedowns_completed_avg" in td_category:
                grappling_metrics["takedowns_avg"] = td_category["takedowns_completed_avg"]
            if "takedowns_attempted_avg" in td_category:
                grappling_metrics["takedown_attempts_avg"] = td_category["takedowns_attempted_avg"]
            if "takedown_accuracy_pct" in td_category:
                grappling_metrics["takedown_accuracy_pct"] = td_category["takedown_accuracy_pct"]
            if grappling_metrics:
                results["grappling"] = grappling_metrics

    return results


async def upsert_fighter_stats(
    session: AsyncSession,
    fighter_id: str,
    aggregated_stats: dict[str, dict[str, str]],
) -> None:
    """Replace fighter_stats rows for a fighter with fresh aggregates."""
    await session.execute(delete(fighter_stats).where(fighter_stats.c.fighter_id == fighter_id))

    rows: list[dict[str, Any]] = []
    for category, metrics in (aggregated_stats or {}).items():
        for metric, raw_value in metrics.items():
            if raw_value is None:
                continue
            rows.append(
                {
                    "fighter_id": fighter_id,
                    "category": category,
                    "metric": metric,
                    "value": str(raw_value),
                }
            )

    if rows:
        await session.execute(insert(fighter_stats), rows)

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

        aggregated_stats = calculate_fighter_stats(fight_history)
        await upsert_fighter_stats(session, fighter_id, aggregated_stats)

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
