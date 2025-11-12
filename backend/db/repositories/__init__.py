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
from backend.db.repositories.event_repository import PostgreSQLEventRepository
from backend.db.repositories.fight_graph_repository import FightGraphRepository
from backend.db.repositories.fight_repository import FightRepository
from backend.db.repositories.fighter import FighterRepository
from backend.db.repositories.postgresql_fighter_repository import (
    PostgreSQLFighterRepository,
)
from backend.db.repositories.stats_repository import StatsRepository

__all__ = [
    "BaseRepository",
    "PostgreSQLFighterRepository",
    "PostgreSQLEventRepository",
    "FighterRepository",
    "FightGraphRepository",
    "StatsRepository",
    "FightRepository",
    "_calculate_age",
    "_empty_breakdown",
    "_invert_fight_result",
    "_normalize_result_category",
]
