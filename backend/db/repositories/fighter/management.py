"""Data management helpers for fighter repositories."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import load_only

from backend.db.models import Fighter


class FighterManagementMixin:
    """Expose persistence helpers for fighter data."""

    async def create_fighter(self, fighter: Fighter) -> Fighter:
        """Create a new fighter in the database."""

        self._session.add(fighter)
        await self._session.flush()
        return fighter

    async def upsert_fighter(self, fighter_data: dict) -> Fighter:
        """Insert or update a fighter based on ID."""

        fighter_id = fighter_data.get("id")

        query = select(Fighter).options(load_only(Fighter.id)).where(Fighter.id == fighter_id)
        result = await self._session.execute(query)
        existing_fighter = result.scalar_one_or_none()

        if existing_fighter:
            for key, value in fighter_data.items():
                if hasattr(existing_fighter, key):
                    setattr(existing_fighter, key, value)
            await self._session.flush()
            return existing_fighter

        fighter = Fighter(**fighter_data)
        self._session.add(fighter)
        await self._session.flush()
        return fighter

    async def update_fighter_location(
        self,
        fighter_id: str,
        *,
        birthplace: str | None = None,
        birthplace_city: str | None = None,
        birthplace_country: str | None = None,
        nationality: str | None = None,
        training_gym: str | None = None,
        training_city: str | None = None,
        training_country: str | None = None,
        ufc_com_slug: str | None = None,
        ufc_com_match_confidence: float | None = None,
        ufc_com_match_method: str | None = None,
        ufc_com_scraped_at: datetime | None = None,
        needs_manual_review: bool | None = None,
    ) -> None:
        """Update fighter location and UFC.com metadata fields."""

        update_values = {}
        if birthplace is not None:
            update_values["birthplace"] = birthplace
        if birthplace_city is not None:
            update_values["birthplace_city"] = birthplace_city
        if birthplace_country is not None:
            update_values["birthplace_country"] = birthplace_country
        if nationality is not None:
            update_values["nationality"] = nationality
        if training_gym is not None:
            update_values["training_gym"] = training_gym
        if training_city is not None:
            update_values["training_city"] = training_city
        if training_country is not None:
            update_values["training_country"] = training_country
        if ufc_com_slug is not None:
            update_values["ufc_com_slug"] = ufc_com_slug
        if ufc_com_match_confidence is not None:
            update_values["ufc_com_match_confidence"] = ufc_com_match_confidence
        if ufc_com_match_method is not None:
            update_values["ufc_com_match_method"] = ufc_com_match_method
        if ufc_com_scraped_at is not None:
            update_values["ufc_com_scraped_at"] = ufc_com_scraped_at
        if needs_manual_review is not None:
            update_values["needs_manual_review"] = needs_manual_review

        if update_values:
            stmt = update(Fighter).where(Fighter.id == fighter_id).values(**update_values)
            await self._session.execute(stmt)

    async def update_fighter_nationality(
        self,
        fighter_id: str,
        nationality: str,
    ) -> None:
        """Update fighter nationality from Sherdog data."""

        stmt = update(Fighter).where(Fighter.id == fighter_id).values(nationality=nationality)
        await self._session.execute(stmt)

    async def get_fighters_without_ufc_com_data(self) -> Sequence[Fighter]:
        """Return fighters lacking UFC.com metadata."""

        stmt = select(Fighter).where(Fighter.ufc_com_slug.is_(None))
        result = await self._session.execute(stmt)
        return result.scalars().all()
