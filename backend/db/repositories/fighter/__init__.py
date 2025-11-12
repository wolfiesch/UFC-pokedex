"""Fighter repository package consolidating modular mixins."""

from __future__ import annotations

from backend.db.repositories.base import BaseRepository
from backend.db.repositories.fighter.columns import FighterColumnMixin
from backend.db.repositories.fighter.comparison import FighterComparisonMixin
from backend.db.repositories.fighter.detail import FighterDetailMixin
from backend.db.repositories.fighter.fight_status import FighterFightStatusMixin
from backend.db.repositories.fighter.management import FighterManagementMixin
from backend.db.repositories.fighter.rankings import FighterRankingMixin
from backend.db.repositories.fighter.roster import FighterRosterMixin
from backend.db.repositories.fighter.streaks import FighterStreakMixin


class FighterRepository(
    FighterDetailMixin,
    FighterComparisonMixin,
    FighterRosterMixin,
    FighterManagementMixin,
    FighterFightStatusMixin,
    FighterRankingMixin,
    FighterStreakMixin,
    FighterColumnMixin,
    BaseRepository,
):
    """Concrete fighter repository combining modular mixins."""

    # The mixin order ensures high-level query helpers resolve before lower-level utilities.


__all__ = ["FighterRepository"]
