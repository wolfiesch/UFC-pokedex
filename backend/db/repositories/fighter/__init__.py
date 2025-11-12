"""Modular fighter repository package.

This package breaks the historical :mod:`fighter_repository` module into
smaller, domain focused components.  External callers import from this module to
maintain a stable API while we reorganise the implementation internals.
"""

from .filters import (
    FighterSearchFilters,
    filter_roster_entries,
    normalize_search_filters,
    paginate_roster_entries,
)
from .ranking import FighterRankingSummary, fetch_ranking_summaries
from .repository import FighterRepository
from .status import fetch_fight_status, normalize_fight_result

__all__ = [
    "FighterRepository",
    "FighterSearchFilters",
    "FighterRankingSummary",
    "fetch_fight_status",
    "fetch_ranking_summaries",
    "filter_roster_entries",
    "normalize_fight_result",
    "normalize_search_filters",
    "paginate_roster_entries",
]
