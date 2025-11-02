"""Unit tests for the data ingestion helpers used by the stats loader."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import fighter_stats
from scripts.load_scraped_data import (
    _average,
    _compute_accuracy,
    _format_number,
    _format_percentage,
    _parse_date,
    _parse_int_stat,
    _parse_landed_attempted,
    _parse_percentage,
    calculate_fighter_stats,
    upsert_fighter_stats,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("25 of 60", (25, 60)),
        ("12/40", (12, 40)),
        ("30 of 30", (30, 30)),
        ("--", None),
        (None, None),
    ],
)
def test_parse_landed_attempted_variants(
    raw: Any, expected: tuple[int, int] | None
) -> None:
    """Ensure landed/attempted strings are normalized into numeric tuples."""
    assert _parse_landed_attempted(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("45%", 0.45),
        ("0.75", 0.75),
        ("75", 0.75),
        (None, None),
        ("--", None),
    ],
)
def test_parse_percentage_variants(raw: Any, expected: float | None) -> None:
    """Validate percentage parsing for strings, integers, and sentinel values."""
    assert _parse_percentage(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("5", 5), (" 10 ", 10), (None, None), ("not-a-number", None)],
)
def test_parse_int_stat_handles_invalid(raw: Any, expected: int | None) -> None:
    """Confirm integer stats gracefully handle blank and malformed inputs."""
    assert _parse_int_stat(raw) == expected


@pytest.mark.parametrize(
    ("value", "formatted"),
    [(12.5, "12.5"), (3.0, "3"), (3.3333, "3.33")],
)
def test_format_number_trims_zeroes(value: float, formatted: str) -> None:
    """The helper should trim trailing zeros but preserve precision where needed."""
    assert _format_number(value) == formatted


@pytest.mark.parametrize(
    ("value", "formatted"),
    [(0.75, "75%"), (0.455, "45.5%"), (1.0, "100%")],
)
def test_format_percentage(value: float, formatted: str) -> None:
    """Percentages are scaled from ratios and rendered without redundant zeros."""
    assert _format_percentage(value) == formatted


@pytest.mark.parametrize(
    ("total", "count", "expected"),
    [(10, 2, 5.0), (0, 3, 0.0), (9, 0, None)],
)
def test_average_handles_zero_counts(
    total: float, count: int, expected: float | None
) -> None:
    """Averages divide totals by sample counts while avoiding division errors."""
    assert _average(total, count) == expected


@pytest.mark.parametrize(
    ("landed", "attempted", "pct_sum", "pct_count", "expected"),
    [
        (30, 40, 0.0, 0, 0.75),
        (0, 0, 1.35, 3, 0.45),
        (0, 0, 0.0, 0, None),
    ],
)
def test_compute_accuracy_prefers_totals(
    landed: int, attempted: int, pct_sum: float, pct_count: int, expected: float | None
) -> None:
    """Accuracy falls back to averaged percentages when raw attempts are missing."""
    assert _compute_accuracy(landed, attempted, pct_sum, pct_count) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2024-03-01", date(2024, 3, 1)),
        (date(2024, 1, 15), date(2024, 1, 15)),
        ("", None),
        ("not-a-date", None),
    ],
)
def test_parse_date_accepts_strings_and_dates(raw: Any, expected: date | None) -> None:
    """Dates from JSON are safely coerced into Python ``date`` objects."""
    assert _parse_date(raw) == expected


def test_calculate_fighter_stats_returns_compact_payload() -> None:
    """Aggregate multiple fights while ignoring missing stat buckets."""
    fights: list[dict[str, Any]] = [
        {
            "stats": {
                "knockdowns": "2",
                "total_strikes": "100",
                "takedowns": "3",
                "submissions": "1",
            }
        },
        {"stats": {"knockdowns": "1", "total_strikes": "80", "takedowns": "1"}},
    ]

    result = calculate_fighter_stats(fights)

    assert result == {
        "striking": {"avg_total_strikes": "90", "avg_knockdowns": "1.5"},
        "grappling": {"avg_takedowns": "2", "avg_submissions": "1"},
        "takedown_stats": {"avg_takedowns": "2"},
    }


@pytest.mark.asyncio
async def test_upsert_fighter_stats_replaces_existing_rows(
    session: AsyncSession,
) -> None:
    """Ensure new aggregate payloads fully replace stale rows for a fighter."""
    initial_payload = {
        "striking": {"avg_total_strikes": "75"},
    }
    await upsert_fighter_stats(session, "fighter-123", initial_payload)
    await session.commit()

    updated_payload = {
        "striking": {"avg_total_strikes": "90"},
        "grappling": {"avg_takedowns": "2"},
    }
    await upsert_fighter_stats(session, "fighter-123", updated_payload)
    await session.commit()

    rows = (
        await session.execute(
            select(
                fighter_stats.c.category,
                fighter_stats.c.metric,
                fighter_stats.c.value,
            ).where(fighter_stats.c.fighter_id == "fighter-123")
        )
    ).all()

    assert sorted(rows) == [
        ("grappling", "avg_takedowns", "2"),
        ("striking", "avg_total_strikes", "90"),
    ]
