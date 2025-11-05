"""Repository package for database access layer.

This package provides specialized repository implementations following
the Single Responsibility Principle, replacing the monolithic repository
with focused, domain-specific repositories.
"""

from backend.db.repositories.base import (
    BaseRepository,
    _calculate_age,
    _empty_breakdown,
    _invert_fight_result,
    _normalize_result_category,
)
from backend.db.repositories.fight_graph_repository import FightGraphRepository
from backend.db.repositories.fight_repository import FightRepository
from backend.db.repositories.fighter_repository import FighterRepository
from backend.db.repositories.stats_repository import StatsRepository

__all__ = [
    "BaseRepository",
    "FighterRepository",
    "FightGraphRepository",
    "StatsRepository",
    "FightRepository",
    "_calculate_age",
    "_empty_breakdown",
    "_invert_fight_result",
    "_normalize_result_category",
]
