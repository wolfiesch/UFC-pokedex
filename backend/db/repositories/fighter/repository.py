"""Concrete fighter repository built from modular mixins."""

from __future__ import annotations

import logging

from backend.db.repositories.fighter.analytics import FighterAnalyticsMixin
from backend.db.repositories.fighter.mutations import FighterMutationMixin
from backend.db.repositories.fighter.roster import FighterRosterMixin

logger = logging.getLogger(__name__)


class FighterRepository(
    FighterMutationMixin,
    FighterAnalyticsMixin,
    FighterRosterMixin,
):
    """Repository for fighter CRUD operations and queries."""

    # The class intentionally inherits behaviour from dedicated mixins.  Each
    # mixin focuses on a thematic slice of the original monolith (roster
    # queries, aggregate analytics, and mutation helpers).  This keeps the
    # public API identical while significantly shrinking per-file complexity.


__all__ = ["FighterRepository"]
