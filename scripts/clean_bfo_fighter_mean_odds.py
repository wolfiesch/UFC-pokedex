#!/usr/bin/env python3
"""Utility script that normalizes BFO fighter odds JSONL files for loading.

The scrapers emit a mixture of legacy (mean_odds_values) and modern
mean_odds_history formats with occasional duplicate rows.  This script
performs the following cleanup steps so the loader and API can rely on a
consistent contract:

1. Validate the presence of ``fighter_id``, ``opponent_name`` and ``event_name``.
2. Normalize the time-series shape, upgrading legacy arrays into the rich
   ``[{timestamp_ms, timestamp, odds}]`` format.  When timestamps are missing we
   synthesize evenly spaced entries anchored to ``scraped_at`` so ordering is
   preserved for charting.
3. Deduplicate rows per ``(fighter_id, opponent_name, event_name)`` keeping the
   highest quality (most data points, freshest scrape, structured history).
4. Assign deterministic odds identifiers (``odds_<md5>``) and quality tiers.
5. Emit the cleaned dataset as JSON Lines along with an optional stats file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

DEFAULT_INPUT = Path("data/raw/bfo_fighter_mean_odds.jsonl")
DEFAULT_OUTPUT = Path("data/processed/bfo_fighter_mean_odds_clean.jsonl")
DEFAULT_STATS = Path("data/processed/bfo_fighter_mean_odds_clean.stats.json")
QUALITY_CHOICES = ("excellent", "good", "usable", "poor", "no_data")


@dataclass(slots=True, frozen=True)
class OddsKey:
    fighter_id: str
    opponent_name: str
    event_name: str

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> OddsKey:
        return cls(
            fighter_id=str(record["fighter_id"]).strip(),
            opponent_name=str(record["opponent_name"]).strip(),
            event_name=str(record["event_name"]).strip(),
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to raw BFO fighter odds JSONL file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Destination for cleaned JSONL output.",
    )
    parser.add_argument(
        "--stats",
        type=Path,
        default=DEFAULT_STATS,
        help="Optional file to write summary statistics (JSON).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process input and log stats without writing cleaned output.",
    )
    return parser.parse_args()


def _parse_scraped_at(value: str | None) -> datetime:
    if not value:
        return datetime.now(tz=UTC)
    cleaned = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        logger.warning("Unable to parse scraped_at '%s'; falling back to now", value)
        return datetime.now(tz=UTC)


def _quality_from_points(points: int) -> str:
    if points > 50:
        return "excellent"
    if points >= 30:
        return "good"
    if points >= 10:
        return "usable"
    if points > 0:
        return "poor"
    return "no_data"


def _ensure_timestamp_pair(timestamp_ms: int | None, timestamp_str: str | None) -> tuple[int, str]:
    """Return a canonical timestamp pair for JSON storage."""

    if timestamp_ms is None and timestamp_str:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        timestamp_ms = int(ts.timestamp() * 1000)
        timestamp_str = ts.astimezone(UTC).isoformat().replace("+00:00", "Z")
    elif timestamp_ms is not None and not timestamp_str:
        ts = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
        timestamp_str = ts.isoformat().replace("+00:00", "Z")
    elif timestamp_ms is not None and timestamp_str:
        # Normalize timezone suffix to Z for consistency.
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        timestamp_str = ts.astimezone(UTC).isoformat().replace("+00:00", "Z")
    else:
        now = datetime.now(tz=UTC)
        timestamp_ms = int(now.timestamp() * 1000)
        timestamp_str = now.isoformat().replace("+00:00", "Z")
    return timestamp_ms, timestamp_str


def _synthesized_history(
    mean_values: list[Any],
    scraped_at: str | None,
) -> list[dict[str, Any]]:
    """Create pseudo timestamps for records lacking structured history."""

    snapshot = _parse_scraped_at(scraped_at)
    step = timedelta(hours=6)
    start = snapshot - step * max(len(mean_values) - 1, 0)
    history: list[dict[str, Any]] = []

    for idx, value in enumerate(mean_values):
        point_time = start + (step * idx)
        odds_value = (
            float(value["odds"])
            if isinstance(value, dict) and "odds" in value
            else float(value)
        )

        timestamp_ms = int(point_time.timestamp() * 1000)
        timestamp = point_time.astimezone(UTC).isoformat().replace("+00:00", "Z")
        history.append(
            {
                "timestamp_ms": timestamp_ms,
                "timestamp": timestamp,
                "odds": odds_value,
            }
        )
    return history


def _normalize_history(record: dict[str, Any]) -> list[dict[str, Any]]:
    if "mean_odds_history" in record and record["mean_odds_history"]:
        normalized: list[dict[str, Any]] = []
        for point in record["mean_odds_history"]:
            timestamp_ms = point.get("timestamp_ms")
            timestamp = point.get("timestamp")
            timestamp_ms, timestamp = _ensure_timestamp_pair(timestamp_ms, timestamp)
            odds = point.get("odds")
            try:
                odds_val = float(odds)
            except (TypeError, ValueError):
                odds_val = None
            if odds_val is None:
                continue
            normalized.append(
                {
                    "timestamp_ms": timestamp_ms,
                    "timestamp": timestamp,
                    "odds": odds_val,
                }
            )
        return normalized

    if "mean_odds_values" in record:
        values = record.get("mean_odds_values") or []
        return _synthesized_history(list(values), record.get("scraped_at"))

    return []


def _make_record_id(key: OddsKey) -> str:
    digest = hashlib.md5(
        f"{key.fighter_id}|{key.opponent_name.lower()}|{key.event_name.lower()}".encode(
            "utf-8"
        )
    ).hexdigest()
    return f"odds_{digest}"


def _score_record(record: dict[str, Any]) -> tuple[int, int, str]:
    history = record.get("mean_odds_history") or []
    explicit_history = 1 if record.get("_original_history") else 0
    num_points = int(record.get("num_odds_points", len(history)))
    scraped_at = record.get("scraped_at") or ""
    return explicit_history, num_points, scraped_at


def _prepare_record(record: dict[str, Any]) -> dict[str, Any] | None:
    required = ("fighter_id", "opponent_name", "event_name")
    if any(record.get(field) in (None, "") for field in required):
        logger.debug("Skipping record missing required field(s): %s", record)
        return None

    key = OddsKey.from_record(record)
    history = _normalize_history(record)

    cleaned = {
        "id": _make_record_id(key),
        "fighter_id": key.fighter_id,
        "opponent_name": key.opponent_name,
        "event_name": key.event_name,
        "event_url": record.get("event_url"),
        "opening_odds": record.get("opening_odds"),
        "closing_range_start": record.get("closing_range_start"),
        "closing_range_end": record.get("closing_range_end"),
        "mean_odds_history": history,
        "num_odds_points": len(history),
        "data_quality_tier": _quality_from_points(len(history)),
        "scraped_at": record.get("scraped_at"),
        "bfo_fighter_url": record.get("fighter_url"),
        "is_duplicate": False,
        "_original_history": bool(record.get("mean_odds_history")),
    }
    return cleaned


def _choose_best_record(records: list[dict[str, Any]]) -> dict[str, Any]:
    records.sort(key=_score_record, reverse=True)
    winner = records[0]
    winner.pop("_original_history", None)
    winner["num_odds_points"] = len(winner["mean_odds_history"])
    winner["data_quality_tier"] = _quality_from_points(winner["num_odds_points"])
    return winner


def clean_records(raw_records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[OddsKey, list[dict[str, Any]]] = defaultdict(list)
    invalid = 0

    for record in raw_records:
        prepared = _prepare_record(record)
        if not prepared:
            invalid += 1
            continue
        key = OddsKey(
            prepared["fighter_id"],
            prepared["opponent_name"],
            prepared["event_name"],
        )
        grouped[key].append(prepared)

    cleaned: list[dict[str, Any]] = []
    quality_counter: Counter[str] = Counter()
    duplicates = 0

    for records in grouped.values():
        if len(records) > 1:
            duplicates += len(records) - 1
        best = _choose_best_record(records)
        quality_counter[best["data_quality_tier"]] += 1
        cleaned.append(best)

    stats = {
        "raw_records": sum(len(v) for v in grouped.values()) + invalid,
        "clean_records": len(cleaned),
        "duplicates_removed": duplicates,
        "dropped_invalid": invalid,
        "quality_distribution": dict(sorted(quality_counter.items())),
    }

    return cleaned, stats


def _load_records(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping invalid JSON line %s: %s", line_no, exc)


def write_cleaned_records(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False))
            handle.write("\n")


def write_stats(stats: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)
        handle.write("\n")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args()

    raw_records = list(_load_records(args.input))
    cleaned, stats = clean_records(raw_records)

    logger.info(
        "Cleaned %s → %s records (duplicates removed: %s, invalid dropped: %s)",
        stats["raw_records"],
        stats["clean_records"],
        stats["duplicates_removed"],
        stats["dropped_invalid"],
    )
    logger.info("Quality distribution: %s", stats["quality_distribution"])

    if not args.dry_run:
        write_cleaned_records(cleaned, args.output)
        write_stats(stats, args.stats)
        logger.info("Wrote cleaned file to %s", args.output)
        logger.info("Wrote stats file to %s", args.stats)
    else:
        logger.info("Dry run requested; no files written.")


if __name__ == "__main__":
    main()
