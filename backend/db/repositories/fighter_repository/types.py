"""Type declarations shared across fighter repository modules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal, TypeVar

# Type alias for valid streak types used when computing fighter streak metadata.
StreakType = Literal["win", "loss", "draw", "none"]

# Generic roster entry used by helper utilities that can operate on
# ``FighterListItem`` instances or richer ``FighterDetail`` records.
RosterEntry = TypeVar("RosterEntry")


@dataclass(frozen=True)
class FighterSearchFilters:
    """Normalized roster search filters shared by multiple repositories."""

    query: str | None
    stance: str | None
    division: str | None
    champion_statuses: tuple[str, ...] | None
    streak_type: StreakType | None
    min_streak_count: int | None


@dataclass
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
