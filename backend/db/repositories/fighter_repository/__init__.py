"""Modular fighter repository package exposing the public API surface."""

from __future__ import annotations

from .filters import (
    filter_roster_entries,
    normalize_search_filters,
    paginate_roster_entries,
)
from .repository import FighterRepository
from .types import FighterRankingSummary, FighterSearchFilters, RosterEntry, StreakType

__all__ = [
    "FighterRepository",
    "FighterRankingSummary",
    "FighterSearchFilters",
    "StreakType",
    "RosterEntry",
    "normalize_search_filters",
    "filter_roster_entries",
    "paginate_roster_entries",
]
