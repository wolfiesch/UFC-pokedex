"""Analytics-focused queries for fighter geography."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from backend.db.models import Fighter


class FighterAnalyticsMixin:
    """Mixin that surfaces geography-based statistics for fighters."""

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
            raise ValueError(f"Invalid group_by value: {group_by}")

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

        stats = []
        for row in rows:
            percentage = round((row.count / total * 100), 1) if total > 0 else 0.0
            stats.append(
                {"country": row.country, "count": row.count, "percentage": percentage}
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
            raise ValueError(f"Invalid group_by value: {group_by}")

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

        stats = []
        for row in rows:
            percentage = round((row.count / total * 100), 1) if total > 0 else 0.0
            stats.append(
                {
                    "city": row.city,
                    "country": row.country,
                    "count": row.count,
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
                Fighter.training_gym, Fighter.training_city, Fighter.training_country
            )
            .order_by(func.count().desc())
        )

        if country:
            query = query.where(Fighter.training_country == country)

        result = await self._session.execute(query)
        rows = result.all()

        stats = []
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
