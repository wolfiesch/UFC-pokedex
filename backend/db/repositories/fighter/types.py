"""Shared type definitions for the fighter repository package."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal, TypeVar

StreakType = Literal["win", "loss", "draw", "none"]
"""Permitted streak type identifiers for roster filtering and streak summaries."""

RosterEntry = TypeVar("RosterEntry")
"""Generic roster entry container used when filtering fighter results."""


@dataclass(frozen=True, slots=True)
class FighterSearchFilters:
    """Normalized roster search filters shared across repository helpers."""

    query: str | None
    stance: str | None
    division: str | None
    nationality: str | None
    champion_statuses: tuple[str, ...] | None
    streak_type: StreakType | None
    min_streak_count: int | None


@dataclass(slots=True)
class FighterRankingSummary:
    """Lightweight bundle of ranking metadata for a fighter."""

    current_rank: int | None = None
    current_rank_date: date | None = None
    current_rank_division: str | None = None
    current_rank_source: str | None = None
    peak_rank: int | None = None
    peak_rank_date: date | None = None
    peak_rank_division: str | None = None
    peak_rank_source: str | None = None
