"""Aggregated fighter analytics queries."""

from __future__ import annotations

import logging
from typing import Any, cast

from sqlalchemy import func, select

from backend.db.models import Fighter
from backend.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class FighterAnalyticsMixin(BaseRepository):
    """Expose aggregate reporting utilities for fighters."""

    async def count_fighters(
        self,
        nationality: str | None = None,
        birthplace_country: str | None = None,
        birthplace_city: str | None = None,
        training_country: str | None = None,
        training_city: str | None = None,
        training_gym: str | None = None,
        has_location_data: bool | None = None,
    ) -> int:
        """Get the total count of fighters in the database with optional filters."""

        query = select(func.count()).select_from(Fighter)

        if nationality:
            logger.debug("Applying nationality filter for count: %s", nationality)
            query = query.where(Fighter.nationality == nationality)
        if birthplace_country:
            query = query.where(Fighter.birthplace_country == birthplace_country)
        if birthplace_city:
            query = query.where(Fighter.birthplace_city == birthplace_city)
        if training_country:
            query = query.where(Fighter.training_country == training_country)
        if training_city:
            query = query.where(Fighter.training_city == training_city)
        if training_gym:
            query = query.where(Fighter.training_gym.ilike(f"%{training_gym}%"))
        if has_location_data is not None:
            from sqlalchemy import or_

            if has_location_data:
                query = query.where(
                    or_(
                        Fighter.birthplace.isnot(None),
                        Fighter.training_gym.isnot(None),
                    )
                )
            else:
                query = query.where(
                    Fighter.birthplace.is_(None),
                    Fighter.training_gym.is_(None),
                )

        result = await self._session.execute(query)
        count = result.scalar_one_or_none()
        return count if count is not None else 0

    async def get_country_stats(
        self, group_by: str
    ) -> tuple[list[dict[str, Any]], int]:
        """Get fighter count by country."""

        if group_by == "birthplace":
            column = Fighter.birthplace_country
        elif group_by == "training":
            column = Fighter.training_country
        elif group_by == "nationality":
            column = Fighter.nationality
        else:
            msg = f"Invalid group_by value: {group_by}"
            raise ValueError(msg)

        query = (
            select(column.label("country"), func.count().label("count"))
            .where(column.isnot(None))
            .group_by(column)
            .order_by(func.count().desc())
        )

        result = await self._session.execute(query)
        rows = result.all()

        roster_total_query = select(func.count()).select_from(Fighter)
        roster_total_result = await self._session.execute(roster_total_query)
        total = roster_total_result.scalar_one_or_none() or 0

        stats: list[dict[str, Any]] = []
        for row in rows:
            count_value = cast(int, row.count)
            percentage = round((count_value / total * 100), 1) if total > 0 else 0.0
            stats.append(
                {
                    "country": row.country,
                    "count": count_value,
                    "percentage": percentage,
                }
            )

        return stats, total

    async def get_city_stats(
        self, group_by: str, country: str | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        """Get fighter count by city."""

        if group_by == "birthplace":
            city_column = Fighter.birthplace_city
            country_column = Fighter.birthplace_country
        elif group_by == "training":
            city_column = Fighter.training_city
            country_column = Fighter.training_country
        else:
            msg = f"Invalid group_by value: {group_by}"
            raise ValueError(msg)

        query = (
            select(
                city_column.label("city"),
                country_column.label("country"),
                func.count().label("count"),
            )
            .where(city_column.isnot(None))
            .group_by(city_column, country_column)
            .order_by(func.count().desc())
        )

        if country:
            query = query.where(country_column == country)

        result = await self._session.execute(query)
        rows = result.all()

        roster_total_query = select(func.count()).select_from(Fighter)
        roster_total_result = await self._session.execute(roster_total_query)
        total = roster_total_result.scalar_one_or_none() or 0

        stats: list[dict[str, Any]] = []
        for row in rows:
            count_value = cast(int, row.count)
            percentage = round((count_value / total * 100), 1) if total > 0 else 0.0
            stats.append(
                {
                    "city": row.city,
                    "country": row.country,
                    "count": count_value,
                    "percentage": percentage,
                }
            )

        return stats, total

    async def get_gym_stats(self, country: str | None = None) -> list[dict[str, Any]]:
        """Get fighter count by gym."""

        query = (
            select(
                Fighter.training_gym.label("gym"),
                Fighter.training_city.label("city"),
                Fighter.training_country.label("country"),
                func.count().label("fighter_count"),
            )
            .where(Fighter.training_gym.isnot(None))
            .group_by(
                Fighter.training_gym,
                Fighter.training_city,
                Fighter.training_country,
            )
            .order_by(func.count().desc())
        )

        if country:
            query = query.where(Fighter.training_country == country)

        result = await self._session.execute(query)
        rows = result.all()

        stats: list[dict[str, Any]] = []
        for row in rows:
            notable_query = (
                select(Fighter.name)
                .where(Fighter.training_gym == row.gym)
                .order_by(Fighter.last_fight_date.desc().nulls_last())
                .limit(2)
            )
            notable_result = await self._session.execute(notable_query)
            notable_fighters = [name for (name,) in notable_result.all()]

            stats.append(
                {
                    "gym": row.gym,
                    "city": row.city,
                    "country": row.country,
                    "fighter_count": row.fighter_count,
                    "notable_fighters": notable_fighters,
                }
            )

        return stats


__all__ = ["FighterAnalyticsMixin"]
