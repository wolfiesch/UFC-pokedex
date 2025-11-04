#!/usr/bin/env python
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

from backend.cache import (
    CacheClient,
    close_redis,
    get_cache_client,
    invalidate_collections,
    invalidate_fighter,
)
from backend.db.connection import get_session
from backend.db.models import Fight, Fighter, fighter_stats

# Load environment variables
load_dotenv()

console = Console()


LANDED_ATTEMPT_RE = re.compile(
    r"(?P<landed>\d+)\s*(?:of|/)\s*(?P<attempted>\d+)", re.IGNORECASE
)
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


def _parse_int_stat(value: Any) -> int | None:
    """Parse simple integer stat values (e.g., '5', '12', etc.)."""
    if value in (None, "", "--"):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


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
    """Return the average of ``total`` over ``count`` while guarding division by zero."""
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


def _parse_fight_duration_seconds(time_value: Any, round_value: Any) -> int | None:
    """Convert round/time metadata into elapsed fight seconds.

    ``time_value`` is expected to be an ``MM:SS`` string, while ``round_value`` is
    the 1-indexed round in which the bout ended. The UFC standard round length is
    five minutes, so the calculation multiplies completed rounds by 300 seconds
    and adds the remaining seconds from ``time_value``. Invalid or missing values
    return ``None`` so the caller can gracefully skip the sample.
    """

    if time_value in (None, "", "--") or round_value in (None, "", "--"):
        return None

    try:
        round_number = int(round_value)
    except (TypeError, ValueError):
        return None

    time_text = str(time_value).strip()
    if not time_text or ":" not in time_text:
        return None

    minutes_text, seconds_text = time_text.split(":", 1)
    try:
        minutes = int(minutes_text)
        seconds = int(seconds_text)
    except ValueError:
        return None

    base_seconds = max(round_number - 1, 0) * 300
    return base_seconds + minutes * 60 + seconds


def _coerce_event_date(value: Any) -> date | None:
    """Attempt to normalise event dates into ``date`` objects for sorting."""

    if isinstance(value, date):
        return value
    if value in (None, "", "--"):
        return None
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def calculate_longest_win_streak(fight_history: list[dict[str, Any]]) -> int:
    """Return the longest consecutive win streak ordered by event date."""

    if not fight_history:
        return 0

    sortable_fights = []
    for fight in fight_history:
        event_date = _coerce_event_date(fight.get("event_date"))
        if event_date is None:
            # Without a date we cannot deterministically place the fight, so skip it.
            continue
        sortable_fights.append((event_date, fight))

    if not sortable_fights:
        return 0

    sortable_fights.sort(key=lambda item: item[0])

    longest = 0
    current = 0
    for _, fight in sortable_fights:
        result = str(fight.get("result", "")).strip().upper()
        if result.startswith("W"):
            current += 1
            longest = max(longest, current)
        elif result:
            current = 0

    return longest


def _store_stat(
    results: dict[str, dict[str, str]],
    category: str,
    metric: str,
    raw_value: Any,
) -> None:
    """Insert a metric into the aggregated results if the value is non-empty."""

    if raw_value in (None, "", "--"):
        return

    value = str(raw_value).strip()
    if not value:
        return

    bucket = results.setdefault(category, {})
    bucket[metric] = value


def calculate_fighter_stats(
    fight_history: list[dict[str, Any]],
    summary_stats: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, str]]:
    """Aggregate per-fight stats into the structure consumed by ``fighter_stats``.

    The routine normalises landed/attempted totals, accuracy percentages, and
    integer counts surfaced in the scraped payload. Metrics are grouped under
    category dictionaries mirroring ``fighter_stats`` rows, including:

    - ``significant_strikes``: tempo, accuracy, and defense metrics.
    - ``striking``: total strike output plus knockdown averages.
    - ``grappling``: takedown volume, accuracy, defence, and submission pressure.
    - ``takedown_stats``: compatibility surface for historic consumers.
    - ``career``: average fight duration (seconds) and longest win streak.
    """

    summary_stats = summary_stats or {}

    def _find_summary_section(keys: set[str]) -> dict[str, Any]:
        for section in summary_stats.values():
            if any(key in section for key in keys):
                return section
        return {}

    sig_totals = {
        "landed": 0,
        "attempted": 0,
        "count": 0,
        "pct_sum": 0.0,
        "pct_count": 0,
    }
    total_strike_totals = {
        "landed": 0,
        "attempted": 0,
        "count": 0,
    }
    takedown_totals = {
        "landed": 0,
        "attempted": 0,
        "count": 0,
    }
    knockdown_totals = {"total": 0, "count": 0}
    submission_totals = {"total": 0, "count": 0}
    durations: list[int] = []

    for fight in fight_history or []:
        stats = fight.get("stats") or {}

        sig_counts = _parse_landed_attempted(stats.get("sig_strikes"))
        if sig_counts is not None:
            landed, attempted = sig_counts
            sig_totals["landed"] += landed
            sig_totals["attempted"] += attempted
            sig_totals["count"] += 1
        else:
            landed = _parse_int_stat(stats.get("sig_strikes"))
            if landed is not None:
                sig_totals["landed"] += landed
                sig_totals["count"] += 1

        sig_pct = _parse_percentage(stats.get("sig_strikes_pct"))
        if sig_pct is not None:
            sig_totals["pct_sum"] += sig_pct
            sig_totals["pct_count"] += 1

        total_strike_counts = _parse_landed_attempted(stats.get("total_strikes"))
        if total_strike_counts is not None:
            landed, attempted = total_strike_counts
            total_strike_totals["landed"] += landed
            total_strike_totals["attempted"] += attempted
            total_strike_totals["count"] += 1
        else:
            landed = _parse_int_stat(stats.get("total_strikes"))
            if landed is not None:
                total_strike_totals["landed"] += landed
                total_strike_totals["count"] += 1

        takedown_counts = _parse_landed_attempted(stats.get("takedowns"))
        if takedown_counts is not None:
            landed, attempted = takedown_counts
            takedown_totals["landed"] += landed
            takedown_totals["attempted"] += attempted
            takedown_totals["count"] += 1
        else:
            landed = _parse_int_stat(stats.get("takedowns"))
            if landed is not None:
                takedown_totals["landed"] += landed
                takedown_totals["count"] += 1

        knockdowns = _parse_int_stat(stats.get("knockdowns"))
        if knockdowns is not None:
            knockdown_totals["total"] += knockdowns
            knockdown_totals["count"] += 1

        submissions = _parse_int_stat(stats.get("submissions"))
        if submissions is not None:
            submission_totals["total"] += submissions
            submission_totals["count"] += 1

        duration_seconds = _parse_fight_duration_seconds(
            fight.get("time"), fight.get("round")
        )
        if duration_seconds is not None:
            durations.append(duration_seconds)

    results: dict[str, dict[str, str]] = {}

    striking_summary = _find_summary_section({"slpm", "str_acc", "sapm", "str_def"})
    grappling_summary = _find_summary_section({"td_avg", "td_acc", "td_def", "sub_avg"})
    significant_summary = summary_stats.get("significant_strikes", {})
    takedown_summary = summary_stats.get("takedown_stats", {})

    STRIKING_SUMMARY_MAP: dict[str, list[tuple[str, str]]] = {
        "slpm": [
            ("significant_strikes", "sig_strikes_landed_per_min"),
            ("striking", "sig_strikes_landed_per_min"),
        ],
        "sapm": [
            ("significant_strikes", "sig_strikes_absorbed_per_min"),
            ("striking", "sig_strikes_absorbed_per_min"),
        ],
        "str_acc": [
            ("significant_strikes", "sig_strikes_accuracy_pct"),
            ("striking", "sig_strikes_accuracy_pct"),
        ],
        "str_def": [
            ("significant_strikes", "sig_strikes_defense_pct"),
            ("striking", "sig_strikes_defense_pct"),
        ],
    }

    for key, targets in STRIKING_SUMMARY_MAP.items():
        value = striking_summary.get(key) or significant_summary.get(key)
        for category, metric in targets:
            _store_stat(results, category, metric, value)

    GRAPPLING_SUMMARY_MAP: dict[str, list[tuple[str, str]]] = {
        "td_avg": [
            ("grappling", "takedowns_avg"),
            ("takedown_stats", "takedowns_completed_avg"),
        ],
        "td_acc": [
            ("grappling", "takedown_accuracy_pct"),
            ("takedown_stats", "takedown_accuracy_pct"),
        ],
        "td_def": [
            ("grappling", "takedown_defense_pct"),
            ("takedown_stats", "takedown_defense_pct"),
        ],
        "sub_avg": [
            ("grappling", "avg_submissions"),
        ],
    }

    for key, targets in GRAPPLING_SUMMARY_MAP.items():
        value = (
            grappling_summary.get(key)
            or takedown_summary.get(key)
            or striking_summary.get(key)
        )
        for category, metric in targets:
            _store_stat(results, category, metric, value)

    # Derived per-fight averages
    if sig_totals["count"] > 0:
        landed_avg = _average(sig_totals["landed"], sig_totals["count"])
        if landed_avg is not None:
            _store_stat(
                results,
                "significant_strikes",
                "sig_strikes_landed_avg",
                _format_number(landed_avg),
            )

    if total_strike_totals["count"] > 0:
        landed_avg = _average(
            total_strike_totals["landed"], total_strike_totals["count"]
        )
        if landed_avg is not None:
            _store_stat(
                results,
                "striking",
                "total_strikes_landed_avg",
                _format_number(landed_avg),
            )

    knockdown_avg = _average(knockdown_totals["total"], knockdown_totals["count"])
    if knockdown_avg is not None:
        _store_stat(
            results,
            "striking",
            "avg_knockdowns",
            _format_number(knockdown_avg),
        )

    if takedown_totals["count"] > 0:
        landed_avg = _average(takedown_totals["landed"], takedown_totals["count"])
        if landed_avg is not None:
            _store_stat(
                results,
                "takedown_stats",
                "takedowns_completed_avg",
                _format_number(landed_avg),
            )
            _store_stat(
                results,
                "grappling",
                "takedowns_avg",
                _format_number(landed_avg),
            )

    submission_avg = _average(submission_totals["total"], submission_totals["count"])
    if submission_avg is not None:
        _store_stat(
            results,
            "grappling",
            "avg_submissions",
            _format_number(submission_avg),
        )
    if submission_totals["total"] > 0:
        _store_stat(
            results,
            "grappling",
            "total_submissions",
            _format_number(float(submission_totals["total"]), decimals=0),
        )

    # Career metrics such as time-in-cage averages and win streaks
    career_metrics: dict[str, str] = {}
    if durations:
        avg_duration = _average(sum(durations), len(durations))
        if avg_duration is not None:
            career_metrics["avg_fight_duration_seconds"] = _format_number(avg_duration)

    longest_streak = calculate_longest_win_streak(fight_history)
    if longest_streak > 0:
        career_metrics["longest_win_streak"] = str(longest_streak)
    if career_metrics:
        results["career"] = career_metrics

    return results


async def upsert_fighter_stats(
    session: AsyncSession,
    fighter_id: str,
    aggregated_stats: dict[str, dict[str, str]],
) -> None:
    """Replace fighter_stats rows for a fighter with fresh aggregates."""
    await session.execute(
        delete(fighter_stats).where(fighter_stats.c.fighter_id == fighter_id)
    )

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
            console.print(
                f"[yellow]Unable to parse date '{value}', storing as NULL[/yellow]"
            )
            return None
    console.print(
        f"[yellow]Unexpected date value type {type(value)!r}; storing as NULL[/yellow]"
    )
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
                        console.print(
                            f"[cyan]Would load fighter: {data.get('name')}[/cyan]"
                        )
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
                    console.print(
                        f"[red]Line {line_num}: Error loading fighter: {e}[/red]"
                    )
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
    cache: CacheClient | None = None,
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
            console.print(
                f"[cyan]Would load detailed data for: {data.get('name')}[/cyan]"
            )
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

        # Delete old fights for this fighter to allow re-scraping with updated data
        await session.execute(delete(Fight).where(Fight.fighter_id == fighter_id))

        # Load fight history
        fight_history = data.get("fight_history", [])
        for fight_data in fight_history:
            fight_id = fight_data.get("fight_id")
            if not fight_id:
                continue

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
                stats=fight_data.get("stats"),
                # The scraped JSON includes an optional textual weight class label
                # that we mirror directly into persistent storage so downstream
                # services (event detail views, fighter timelines, etc.) can render
                # the division context without re-scraping the event artifact.
                weight_class=fight_data.get("weight_class"),
            )
            await session.merge(fight)

        summary_payload = {
            key: data.get(key) or {}
            for key in (
                "career_statistics",
                "striking",
                "grappling",
                "significant_strikes",
                "takedown_stats",
                "career",
            )
        }
        summary_payload = {
            key: value for key, value in summary_payload.items() if value
        }

        aggregated_stats = calculate_fighter_stats(
            fight_history,
            summary_stats=summary_payload,
        )
        await upsert_fighter_stats(session, fighter_id, aggregated_stats)

        await session.commit()
        if cache is not None and not dry_run:
            await invalidate_fighter(cache, fighter_id)
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
        console.print(
            "[yellow]DRY RUN MODE - No data will be written to database[/yellow]\n"
        )

    cache_client: CacheClient | None = None
    if not args.dry_run:
        try:
            cache_client = await get_cache_client()
        except Exception as cache_error:  # pragma: no cover - best effort logging
            console.print(
                f"[yellow]Warning: unable to connect to Redis cache ({cache_error}). Proceeding without caching.[/yellow]"
            )
            cache_client = None

    async with get_session() as session:
        if args.fighter_id:
            # Load specific fighter detail
            detail_path = Path(f"data/processed/fighters/{args.fighter_id}.json")
            success = await load_fighter_detail(
                session,
                detail_path,
                dry_run=args.dry_run,
                cache=cache_client,
            )
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

            console.print(
                f"\n[green]✓ Loaded {loaded_count} fighters from list[/green]"
            )

            # Optionally load detailed data for all fighters
            if args.load_details:
                fighters_dir = Path("data/processed/fighters")
                if fighters_dir.exists():
                    fighter_files = list(fighters_dir.glob("*.json"))
                    console.print(
                        f"\n[blue]Loading detailed data for {len(fighter_files)} fighters...[/blue]"
                    )

                    success_count = 0
                    for fighter_file in fighter_files:
                        if args.limit and success_count >= args.limit:
                            break

                        success = await load_fighter_detail(
                            session,
                            fighter_file,
                            dry_run=args.dry_run,
                            cache=cache_client,
                        )
                        if success:
                            success_count += 1

                    console.print(
                        f"[green]✓ Loaded detailed data for {success_count} fighters[/green]"
                    )

    if cache_client is not None and not args.dry_run:
        await invalidate_collections(cache_client)
        # Close Redis connection gracefully
        await close_redis()

    console.print("\n[bold green]Data loading complete![/bold green]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load scraped fighter data into database"
    )
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
