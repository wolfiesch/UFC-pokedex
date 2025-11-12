"""Roster level operations for fighter repositories."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime
from typing import Any, Literal
from typing import cast as typing_cast

from sqlalchemy import func, or_, select
from sqlalchemy.orm import load_only

from backend.db.models import Fighter
from backend.db.repositories.base import _calculate_age
from backend.db.repositories.fighter.filters import (
    _validate_streak_type,
    normalize_search_filters,
)
from backend.schemas.fighter import FighterListItem
from backend.services.image_resolver import resolve_fighter_image

logger = logging.getLogger(__name__)


class FighterRosterMixin:
    """Provide list, search, and aggregation helpers for fighters."""

    async def list_fighters(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        nationality: str | None = None,
        birthplace_country: str | None = None,
        birthplace_city: str | None = None,
        training_country: str | None = None,
        training_city: str | None = None,
        training_gym: str | None = None,
        has_location_data: bool | None = None,
        include_streak: bool = False,
        streak_window: int = 6,
    ) -> Iterable[FighterListItem]:
        """List all fighters with optional pagination and filters."""

        base_columns = self._fighter_summary_columns()
        load_columns, supports_was_interim = await self._resolve_fighter_columns(
            base_columns
        )

        query = (
            select(Fighter)
            .options(load_only(*load_columns))
            .order_by(
                Fighter.last_fight_date.desc().nulls_last(), Fighter.name, Fighter.id
            )
        )

        if nationality:
            logger.debug("Applying nationality filter: %s", nationality)
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

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        result = await self._session.execute(query)
        fighters = result.scalars().all()
        fighter_ids = [f.id for f in fighters]

        streak_by_fighter: dict[
            str, dict[str, int | Literal["win", "loss", "draw", "none"]]
        ] = {}
        if include_streak and fighters:
            streak_by_fighter = await self._batch_compute_streaks(
                fighter_ids, window=streak_window
            )

        fight_status_by_fighter: dict[
            str, dict[str, date | Literal["win", "loss", "draw", "nc"] | None]
        ] = {}
        if fighters:
            fight_status_by_fighter = await self._fetch_fight_status(fighter_ids)

        rankings = await self._fetch_ranking_summaries(fighter_ids)

        today_utc = datetime.now(tz=UTC).date()
        roster_entries: list[FighterListItem] = []
        for fighter in fighters:
            streak_bundle = streak_by_fighter.get(fighter.id, {})
            fight_status = fight_status_by_fighter.get(fighter.id, {})
            ranking = rankings.get(fighter.id)
            roster_entries.append(
                FighterListItem(
                    fighter_id=fighter.id,
                    detail_url=f"http://www.ufcstats.com/fighter-details/{fighter.id}",
                    name=fighter.name,
                    nickname=fighter.nickname,
                    record=fighter.record,
                    division=fighter.division,
                    height=fighter.height,
                    weight=fighter.weight,
                    reach=fighter.reach,
                    stance=fighter.stance,
                    dob=fighter.dob,
                    age=_calculate_age(dob=fighter.dob, reference_date=today_utc),
                    image_url=resolve_fighter_image(fighter.id, fighter.image_url),
                    is_current_champion=fighter.is_current_champion,
                    is_former_champion=fighter.is_former_champion,
                    was_interim=fighter.was_interim if supports_was_interim else False,
                    current_streak_type=typing_cast(
                        Literal["win", "loss", "draw", "none"],
                        (
                            streak_bundle.get("current_streak_type", "none")
                            if include_streak
                            else "none"
                        ),
                    ),
                    current_streak_count=(
                        int(streak_bundle.get("current_streak_count", 0))
                        if include_streak
                        else 0
                    ),
                    current_rank=ranking.current_rank if ranking else None,
                    current_rank_date=ranking.current_rank_date if ranking else None,
                    current_rank_division=(
                        ranking.current_rank_division if ranking else None
                    ),
                    current_rank_source=(
                        ranking.current_rank_source if ranking else None
                    ),
                    peak_rank=ranking.peak_rank if ranking else None,
                    peak_rank_date=ranking.peak_rank_date if ranking else None,
                    peak_rank_division=ranking.peak_rank_division if ranking else None,
                    peak_rank_source=ranking.peak_rank_source if ranking else None,
                    birthplace=fighter.birthplace,
                    birthplace_city=fighter.birthplace_city,
                    birthplace_country=fighter.birthplace_country,
                    nationality=fighter.nationality,
                    fighting_out_of=fighter.fighting_out_of,
                    training_gym=fighter.training_gym,
                    training_city=fighter.training_city,
                    training_country=fighter.training_country,
                    next_fight_date=typing_cast(
                        date | None, fight_status.get("next_fight_date")
                    ),
                    last_fight_date=fighter.last_fight_date,
                    last_fight_result=typing_cast(
                        Literal["win", "loss", "draw", "nc"] | None,
                        fight_status.get("last_fight_result"),
                    ),
                )
            )

        return roster_entries

    async def search_fighters(
        self,
        *,
        query: str | None = None,
        stance: str | None = None,
        division: str | None = None,
        champion_statuses: Sequence[str] | None = None,
        streak_type: str | None = None,
        min_streak_count: int | None = None,
        limit: int | None = None,
        offset: int | None = None,
        include_streak: bool = False,
        streak_window: int = 6,
        include_locations: bool = True,
    ) -> tuple[list[FighterListItem], int]:
        """Search fighters with optional filters and pagination."""

        filters = normalize_search_filters(
            query=query,
            stance=stance,
            division=division,
            champion_statuses=champion_statuses,
            streak_type=streak_type,
            min_streak_count=min_streak_count,
        )

        base_columns = self._fighter_summary_columns()
        load_columns, supports_was_interim = await self._resolve_fighter_columns(
            base_columns
        )

        # Build query with database-level filtering for performance
        query_stmt = select(Fighter).options(load_only(*load_columns))

        # Apply text search at database level
        if filters.query:
            search_pattern = f"%{filters.query}%"
            search_conditions = [
                Fighter.name.ilike(search_pattern),
                Fighter.nickname.ilike(search_pattern),
            ]
            if include_locations:
                search_conditions.extend(
                    [
                        Fighter.birthplace.ilike(search_pattern),
                        Fighter.training_gym.ilike(search_pattern),
                        Fighter.nationality.ilike(search_pattern),
                        Fighter.fighting_out_of.ilike(search_pattern),
                    ]
                )
            query_stmt = query_stmt.where(or_(*search_conditions))

        # Apply stance filter at database level
        if filters.stance:
            query_stmt = query_stmt.where(Fighter.stance.ilike(filters.stance))

        # Apply division filter at database level
        if filters.division:
            query_stmt = query_stmt.where(Fighter.division.ilike(filters.division))

        # Apply champion status filters at database level
        if filters.champion_statuses:
            champion_conditions = []
            for status in filters.champion_statuses:
                if status == "current":
                    champion_conditions.append(Fighter.is_current_champion.is_(True))
                elif status == "former":
                    champion_conditions.append(Fighter.is_former_champion.is_(True))
                elif status == "interim":
                    champion_conditions.append(Fighter.was_interim.is_(True))
            if champion_conditions:
                query_stmt = query_stmt.where(or_(*champion_conditions))

        query_stmt = query_stmt.order_by(Fighter.name, Fighter.id)

        # Get total count before pagination
        count_stmt = select(func.count()).select_from(query_stmt.subquery())
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        # Apply pagination at database level
        if offset is not None:
            query_stmt = query_stmt.offset(offset)
        if limit is not None:
            query_stmt = query_stmt.limit(limit)

        result = await self._session.execute(query_stmt)
        fighters = result.scalars().all()
        fighter_ids = [f.id for f in fighters]

        # Fetch streak data if requested
        streak_by_fighter: dict[
            str, dict[str, int | Literal["win", "loss", "draw", "none"]]
        ] = {}
        if include_streak and fighter_ids:
            streak_by_fighter = await self._batch_compute_streaks(
                fighter_ids, window=streak_window
            )

        # Apply streak filter in-memory (can't be done efficiently at DB level)
        if filters.streak_type and filters.min_streak_count is not None:
            filtered_fighters = []
            for fighter in fighters:
                streak_bundle = streak_by_fighter.get(fighter.id, {})
                fighter_streak_type = streak_bundle.get("current_streak_type", "none")
                fighter_streak_count = int(streak_bundle.get("current_streak_count", 0))
                if (
                    fighter_streak_type == filters.streak_type
                    and fighter_streak_count >= filters.min_streak_count
                ):
                    filtered_fighters.append(fighter)
            fighters = filtered_fighters
            fighter_ids = [f.id for f in fighters]
            total = len(fighters)

        rankings = await self._fetch_ranking_summaries(fighter_ids)
        fight_status_by_fighter = await self._fetch_fight_status(fighter_ids)

        today_utc = datetime.now(tz=UTC).date()
        roster_entries: list[FighterListItem] = []
        for fighter in fighters:
            streak_bundle = streak_by_fighter.get(fighter.id, {})
            fight_status = fight_status_by_fighter.get(fighter.id, {})
            ranking = rankings.get(fighter.id)
            roster_entries.append(
                FighterListItem(
                    fighter_id=fighter.id,
                    detail_url=f"http://www.ufcstats.com/fighter-details/{fighter.id}",
                    name=fighter.name,
                    nickname=fighter.nickname,
                    record=fighter.record,
                    division=fighter.division,
                    height=fighter.height,
                    weight=fighter.weight,
                    reach=fighter.reach,
                    stance=fighter.stance,
                    dob=fighter.dob,
                    age=_calculate_age(dob=fighter.dob, reference_date=today_utc),
                    image_url=resolve_fighter_image(fighter.id, fighter.image_url),
                    is_current_champion=fighter.is_current_champion,
                    is_former_champion=fighter.is_former_champion,
                    was_interim=fighter.was_interim if supports_was_interim else False,
                    current_streak_type=(
                        _validate_streak_type(
                            typing_cast(
                                str | None, streak_bundle.get("current_streak_type")
                            )
                        )
                        if include_streak
                        else "none"
                    )
                    or "none",
                    current_streak_count=(
                        int(streak_bundle.get("current_streak_count", 0))
                        if include_streak
                        else 0
                    ),
                    current_rank=ranking.current_rank if ranking else None,
                    current_rank_date=ranking.current_rank_date if ranking else None,
                    current_rank_division=(
                        ranking.current_rank_division if ranking else None
                    ),
                    current_rank_source=(
                        ranking.current_rank_source if ranking else None
                    ),
                    peak_rank=ranking.peak_rank if ranking else None,
                    peak_rank_date=ranking.peak_rank_date if ranking else None,
                    peak_rank_division=ranking.peak_rank_division if ranking else None,
                    peak_rank_source=ranking.peak_rank_source if ranking else None,
                    birthplace=fighter.birthplace,
                    birthplace_city=fighter.birthplace_city,
                    birthplace_country=fighter.birthplace_country,
                    nationality=fighter.nationality,
                    fighting_out_of=fighter.fighting_out_of,
                    training_gym=fighter.training_gym,
                    training_city=fighter.training_city,
                    training_country=fighter.training_country,
                    next_fight_date=typing_cast(
                        date | None, fight_status.get("next_fight_date")
                    ),
                    last_fight_date=fighter.last_fight_date,
                    last_fight_result=typing_cast(
                        Literal["win", "loss", "draw", "nc"] | None,
                        fight_status.get("last_fight_result"),
                    ),
                )
            )

        return roster_entries, total

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
        """Return the number of fighters that match the supplied filters."""

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

    async def get_random_fighter(self) -> FighterListItem | None:
        """Return a random fighter snapshot."""

        base_columns = self._fighter_summary_columns()
        load_columns, _ = await self._resolve_fighter_columns(
            base_columns, include_was_interim=False
        )
        query = (
            select(Fighter)
            .options(load_only(*load_columns))
            .order_by(func.random())
            .limit(1)
        )
        result = await self._session.execute(query)
        fighter = result.scalar_one_or_none()

        if fighter is None:
            return None

        ranking = (await self._fetch_ranking_summaries([fighter.id])).get(fighter.id)

        return FighterListItem(
            fighter_id=fighter.id,
            detail_url=f"http://www.ufcstats.com/fighter-details/{fighter.id}",
            name=fighter.name,
            nickname=fighter.nickname,
            division=fighter.division,
            height=fighter.height,
            weight=fighter.weight,
            reach=fighter.reach,
            stance=fighter.stance,
            dob=fighter.dob,
            image_url=resolve_fighter_image(fighter.id, fighter.image_url),
            current_rank=ranking.current_rank if ranking else None,
            current_rank_date=ranking.current_rank_date if ranking else None,
            current_rank_division=ranking.current_rank_division if ranking else None,
            current_rank_source=ranking.current_rank_source if ranking else None,
            peak_rank=ranking.peak_rank if ranking else None,
            peak_rank_date=ranking.peak_rank_date if ranking else None,
            peak_rank_division=ranking.peak_rank_division if ranking else None,
            peak_rank_source=ranking.peak_rank_source if ranking else None,
            birthplace=fighter.birthplace,
            birthplace_city=fighter.birthplace_city,
            birthplace_country=fighter.birthplace_country,
            nationality=fighter.nationality,
            fighting_out_of=fighter.fighting_out_of,
            training_gym=fighter.training_gym,
            training_city=fighter.training_city,
            training_country=fighter.training_country,
        )

    async def get_country_stats(
        self, group_by: str
    ) -> tuple[list[dict[str, Any]], int]:
        """Aggregate fighter counts grouped by country metadata."""

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
            percentage = round((row.count / total * 100), 1) if total > 0 else 0.0
            stats.append(
                {"country": row.country, "count": row.count, "percentage": percentage}
            )

        return stats, total

    async def get_city_stats(
        self, group_by: str, country: str | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        """Aggregate fighter counts grouped by city metadata."""

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
        """Aggregate fighter counts by training gym."""

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

        # Fetch notable fighters in a single query using window function
        gym_names = [row.gym for row in rows]
        notable_by_gym: dict[str, list[str]] = {}

        if gym_names:
            from sqlalchemy import text

            notable_query = text(
                """
                WITH ranked_fighters AS (
                    SELECT
                        name,
                        training_gym,
                        ROW_NUMBER() OVER(
                            PARTITION BY training_gym
                            ORDER BY last_fight_date DESC NULLS LAST
                        ) as rn
                    FROM fighter
                    WHERE training_gym = ANY(:gym_names)
                )
                SELECT name, training_gym
                FROM ranked_fighters
                WHERE rn <= 2
            """
            )
            notable_result = await self._session.execute(
                notable_query, {"gym_names": gym_names}
            )

            for name, gym in notable_result:
                notable_by_gym.setdefault(gym, []).append(name)

        stats: list[dict[str, Any]] = []
        for row in rows:
            stats.append(
                {
                    "gym": row.gym,
                    "city": row.city,
                    "country": row.country,
                    "fighter_count": row.fighter_count,
                    "notable_fighters": notable_by_gym.get(row.gym, []),
                }
            )

        return stats
