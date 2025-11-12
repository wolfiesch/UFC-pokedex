"""Roster-facing queries for fighter data."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Literal, cast

from sqlalchemy import func, select
from sqlalchemy.orm import load_only

from backend.db.models import Fighter
from backend.services.image_resolver import resolve_fighter_image

from .fight_status import fetch_fight_status
from .filters import normalize_search_filters
from .logger import LOGGER
from .ranking import fetch_ranking_summaries
from .streaks import batch_compute_streaks


class FighterRosterMixin:
    """Mixin encapsulating roster list and search operations."""

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
    ) -> list["FighterListItem"]:
        """List all fighters with optional pagination."""

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
            LOGGER.debug("Applying nationality filter: %s", nationality)
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
            streak_by_fighter = await batch_compute_streaks(
                self._session, fighter_ids, window=streak_window
            )

        fight_status_by_fighter: dict[
            str, dict[str, date | Literal["win", "loss", "draw", "nc"] | None]
        ] = {}
        if fighters:
            fight_status_by_fighter = await fetch_fight_status(
                self._session, fighter_ids
            )

        ranking_summaries = (
            await fetch_ranking_summaries(
                self._session, fighter_ids, ranking_source=self._ranking_source()
            )
            if fighters
            else {}
        )

        today_utc: date = datetime.now(tz=UTC).date()

        roster_entries: list["FighterListItem"] = []
        for fighter in fighters:
            streak_bundle = streak_by_fighter.get(fighter.id, {})
            fight_status = fight_status_by_fighter.get(fighter.id, {})
            ranking = ranking_summaries.get(fighter.id)
            roster_entries.append(
                self._build_roster_entry(
                    fighter=fighter,
                    supports_was_interim=supports_was_interim,
                    include_streak=include_streak,
                    streak_bundle=streak_bundle,
                    fight_status=fight_status,
                    ranking=ranking,
                    today_utc=today_utc,
                )
            )
        return roster_entries

    async def search_fighters(
        self,
        query: str | None = None,
        stance: str | None = None,
        division: str | None = None,
        champion_statuses: list[str] | None = None,
        streak_type: str | None = None,
        min_streak_count: int | None = None,
        include_locations: bool = True,
        include_streak: bool = False,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[list["FighterListItem"], int]:
        """Search fighters by name, stance, division, champion status, or streak."""

        filters = []
        normalized_filters = normalize_search_filters(
            query=query,
            stance=stance,
            division=division,
            champion_statuses=champion_statuses,
            streak_type=streak_type,
            min_streak_count=min_streak_count,
        )

        if normalized_filters.query:
            pattern = f"%{normalized_filters.query}%"
            search_conditions = [
                Fighter.name.ilike(pattern),
                Fighter.nickname.ilike(pattern),
            ]

            if include_locations:
                search_conditions.extend(
                    [
                        Fighter.birthplace.ilike(pattern),
                        Fighter.birthplace_city.ilike(pattern),
                        Fighter.birthplace_country.ilike(pattern),
                        Fighter.nationality.ilike(pattern),
                        Fighter.training_gym.ilike(pattern),
                        Fighter.training_city.ilike(pattern),
                        Fighter.training_country.ilike(pattern),
                    ]
                )

            from sqlalchemy import or_

            filters.append(or_(*search_conditions))
        if normalized_filters.stance:
            filters.append(Fighter.stance == normalized_filters.stance)
        if normalized_filters.division:
            filters.append(Fighter.division == normalized_filters.division)

        if normalized_filters.champion_statuses:
            supports_was_interim = await self._supports_was_interim()
            champion_conditions = []
            for status in normalized_filters.champion_statuses:
                if status == "current":
                    champion_conditions.append(Fighter.is_current_champion.is_(True))
                elif status == "former":
                    champion_conditions.append(Fighter.is_former_champion.is_(True))
                elif status == "interim" and supports_was_interim:
                    champion_conditions.append(Fighter.was_interim.is_(True))
            if champion_conditions:
                from sqlalchemy import or_

                filters.append(or_(*champion_conditions))

        if (
            normalized_filters.streak_type
            and normalized_filters.min_streak_count is not None
        ):
            filters.append(
                Fighter.current_streak_type == normalized_filters.streak_type
            )
            filters.append(
                Fighter.current_streak_count >= normalized_filters.min_streak_count
            )

        base_columns = self._fighter_summary_columns()
        load_columns, supports_was_interim = await self._resolve_fighter_columns(
            base_columns
        )
        stmt = (
            select(Fighter)
            .options(load_only(*load_columns))
            .order_by(Fighter.last_fight_date.desc().nulls_last(), Fighter.name)
        )
        count_stmt = select(func.count()).select_from(Fighter)

        for condition in filters:
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        if offset is not None and offset > 0:
            stmt = stmt.offset(offset)
        if limit is not None and limit > 0:
            stmt = stmt.limit(limit)

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one_or_none() or 0

        result = await self._session.execute(stmt)
        fighters = result.scalars().all()
        fighter_ids = [f.id for f in fighters]
        ranking_summaries = (
            await fetch_ranking_summaries(
                self._session, fighter_ids, ranking_source=self._ranking_source()
            )
            if fighter_ids
            else {}
        )

        fight_status_by_fighter: dict[
            str, dict[str, date | Literal["win", "loss", "draw", "nc"] | None]
        ] = {}
        if fighter_ids:
            fight_status_by_fighter = await fetch_fight_status(
                self._session, fighter_ids
            )

        today_utc: date = datetime.now(tz=UTC).date()

        roster_entries: list["FighterListItem"] = []
        for fighter in fighters:
            fight_status = fight_status_by_fighter.get(fighter.id, {})
            ranking = ranking_summaries.get(fighter.id)
            roster_entries.append(
                self._build_roster_entry(
                    fighter=fighter,
                    supports_was_interim=supports_was_interim,
                    include_streak=include_streak,
                    streak_bundle={},
                    fight_status=fight_status,
                    ranking=ranking,
                    today_utc=today_utc,
                )
            )

        return roster_entries, cast(int, total)

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
            LOGGER.debug("Applying nationality filter for count: %s", nationality)
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
        return cast(int, count or 0)

    async def get_random_fighter(
        self,
    ) -> "FighterListItem" | None:
        """Get a random fighter from the database."""

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

        ranking = (
            await fetch_ranking_summaries(
                self._session, [fighter.id], ranking_source=self._ranking_source()
            )
        ).get(fighter.id)

        return self._build_roster_entry(
            fighter=fighter,
            supports_was_interim=False,
            include_streak=False,
            streak_bundle={},
            fight_status={},
            ranking=ranking,
            today_utc=datetime.now(tz=UTC).date(),
        )
