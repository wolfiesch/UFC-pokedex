"""Fight repository for fight-focused CRUD operations.

This repository handles:
- Fight record CRUD
- Currently minimal but ready for growth as fight-specific features are added
"""

from __future__ import annotations

from backend.db.models import Fight
from backend.db.repositories.base import BaseRepository


class FightRepository(BaseRepository):
    """Repository for fight CRUD operations."""

    async def create_fight(self, fight: Fight) -> Fight:
        """Create a new fight record in the database."""
        self._session.add(fight)
        await self._session.flush()
        return fight
