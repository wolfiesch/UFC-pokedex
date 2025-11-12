"""Backwards compatible import for the modular fighter repository package."""

from __future__ import annotations

from datetime import datetime

from backend.db.repositories.fighter import FighterRepository
from backend.db.repositories.fighter.filters import (
    FighterSearchFilters,
    filter_roster_entries,
    normalize_search_filters,
    paginate_roster_entries,
)
from backend.db.repositories.fighter.types import FighterRankingSummary, StreakType

__all__ = [
    "FighterRepository",
    "FighterSearchFilters",
    "filter_roster_entries",
    "normalize_search_filters",
    "paginate_roster_entries",
    "FighterRankingSummary",
    "StreakType",
    "datetime",  # For backward compatibility with tests that patch this module
]
