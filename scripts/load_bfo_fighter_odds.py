#!/usr/bin/env python3
"""Bulk loader for cleaned BestFightOdds fighter mean odds data."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from datetime import UTC, datetime, date
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.db.connection import create_engine, create_session_factory, get_database_url
from backend.db.models import Fighter, FighterOdds
from backend.db.models.odds import QUALITY_CHOICES

logger = logging.getLogger(__name__)

DEFAULT_INPUT = Path("data/processed/bfo_fighter_mean_odds_clean.jsonl")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Cleaned JSONL file produced by clean_bfo_fighter_mean_odds.py",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Override DATABASE_URL for loading (defaults to environment).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=250,
        help="Number of rows to upsert per transaction batch.",
    )
    parser.add_argument(
        "--skip-missing-fighters",
        dest="skip_missing_fighters",
        action="store_true",
        default=True,
        help="Drop rows whose fighter_id does not exist in the database (default).",
    )
    parser.add_argument(
        "--allow-missing-fighters",
        dest="skip_missing_fighters",
        action="store_false",
        help="Insert rows even if the fighter_id has not been seeded yet.",
    )
    return parser.parse_args()


def _resolve_database_url(cli_url: str | None) -> str:
    if cli_url:
        os.environ["DATABASE_URL"] = cli_url
    return get_database_url()


def _sanitize_database_url(url: str) -> str:
    if "://" not in url or "@" not in url:
        return url
    scheme, rest = url.split("://", 1)
    auth, host = rest.split("@", 1)
    if ":" in auth:
        user, _ = auth.split(":", 1)
        auth = f"{user}:***"
    return f"{scheme}://{auth}@{host}"


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        logger.warning("Invalid event_date '%s'; storing NULL", value)
        return None


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(tz=UTC)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("Invalid scraped_at '%s'; substituting current time", value)
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


def _prepare_payload(record: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "id": record["id"],
        "fighter_id": record["fighter_id"],
        "opponent_name": record["opponent_name"],
        "event_name": record["event_name"],
        "event_url": record.get("event_url"),
        "event_date": _parse_date(record.get("event_date")),
        "opening_odds": record.get("opening_odds"),
        "closing_range_start": record.get("closing_range_start"),
        "closing_range_end": record.get("closing_range_end"),
        "mean_odds_history": record.get("mean_odds_history") or [],
        "num_odds_points": int(record.get("num_odds_points", 0)),
        "data_quality_tier": record.get("data_quality_tier"),
        "is_duplicate": bool(record.get("is_duplicate", False)),
        "scraped_at": _parse_datetime(record.get("scraped_at")),
        "bfo_fighter_url": record.get("bfo_fighter_url"),
    }
    if not payload["mean_odds_history"]:
        payload["num_odds_points"] = 0
        payload["data_quality_tier"] = "no_data"
    else:
        payload["num_odds_points"] = len(payload["mean_odds_history"])

    quality = payload.get("data_quality_tier")
    if quality not in QUALITY_CHOICES:
        payload["data_quality_tier"] = _quality_from_points(payload["num_odds_points"])

    return payload


def _iter_clean_records(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            yield json.loads(line)


async def _fetch_existing_fighters(session: AsyncSession) -> set[str]:
    result = await session.execute(select(Fighter.id))
    return set(result.scalars().all())


async def _upsert_batch(session: AsyncSession, batch: list[dict[str, Any]]) -> None:
    if not batch:
        return
    stmt = insert(FighterOdds).values(batch)
    update_columns = {
        column: getattr(stmt.excluded, column)
        for column in (
            "fighter_id",
            "opponent_name",
            "event_name",
            "event_url",
            "event_date",
            "opening_odds",
            "closing_range_start",
            "closing_range_end",
            "mean_odds_history",
            "num_odds_points",
            "data_quality_tier",
            "is_duplicate",
            "scraped_at",
            "bfo_fighter_url",
        )
    }
    stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_columns)
    await session.execute(stmt)


async def load_odds_data(
    path: Path,
    engine: AsyncEngine,
    *,
    batch_size: int,
    skip_missing_fighters: bool,
) -> dict[str, int]:
    session_factory: sessionmaker[AsyncSession] = create_session_factory(engine)
    async with session_factory() as session:
        fighter_ids = await _fetch_existing_fighters(session)
        logger.info("Loaded %s fighter ids from database", len(fighter_ids))

        processed = 0
        skipped = 0
        batch: list[dict[str, Any]] = []

        for record in _iter_clean_records(path):
            fighter_id = record.get("fighter_id")
            if skip_missing_fighters and fighter_id not in fighter_ids:
                # [*TO-DO*] - Add debug logging for skipped fighters:
                # logger.debug("Skipping odds for missing fighter_id=%s (opponent=%s, event=%s)",
                #              fighter_id, record.get("opponent_name"), record.get("event_name"))
                skipped += 1
                continue

            payload = _prepare_payload(record)
            batch.append(payload)
            processed += 1

            if len(batch) >= batch_size:
                await _upsert_batch(session, batch)
                await session.commit()
                batch.clear()

        if batch:
            await _upsert_batch(session, batch)
            await session.commit()

    return {"processed": processed, "skipped": skipped}


async def async_main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args()

    database_url = _resolve_database_url(args.database_url)
    logger.info("Using database %s", _sanitize_database_url(database_url))
    engine = create_engine()
    logger.info("Loading odds data from %s", args.input)

    try:
        stats = await load_odds_data(
            args.input,
            engine,
            batch_size=args.batch_size,
            skip_missing_fighters=args.skip_missing_fighters,
        )
    finally:
        await engine.dispose()

    logger.info(
        "Upserted %s records (skipped %s missing fighters)",
        stats["processed"],
        stats["skipped"],
    )


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
