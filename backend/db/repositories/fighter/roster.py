"""Roster centric operations for the fighter repository."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any, Iterable, Literal, Sequence
from typing import cast as typing_cast

from sqlalchemy import func, literal, select
from sqlalchemy.orm import load_only

from backend.db.models import Fight, Fighter, fighter_stats
from backend.db.repositories.base import _calculate_age, _invert_fight_result
from backend.db.repositories.fighter.columns import (
    fighter_comparison_columns,
    fighter_detail_columns,
    fighter_summary_columns,
)
from backend.db.repositories.fighter.filters import _validate_streak_type
from backend.db.repositories.fighter.ranking import fetch_ranking_summaries
from backend.db.repositories.fighter.status import fetch_fight_status
from backend.db.repositories.fighter.streaks import FighterStreakMixin
from backend.db.repositories.fight_utils import (
    compute_record_from_fights,
    create_fight_key,
    should_replace_fight,
    sort_fight_history,
)
from backend.schemas.fighter import (
    FighterComparisonEntry,
    FighterDetail,
    FighterListItem,
    FightHistoryEntry,
)
from backend.services.image_resolver import resolve_fighter_image
from pydantic import HttpUrl

logger = logging.getLogger(__name__)


def _fighter_detail_url(fighter_id: str) -> HttpUrl:
    """Return the canonical UFCStats detail URL for ``fighter_id``."""

    return typing_cast(HttpUrl, f"http://www.ufcstats.com/fighter-details/{fighter_id}")


class FighterRosterMixin(FighterStreakMixin):
    """Provide roster level read operations for fighter repositories."""

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
        """List all fighters with optional pagination and streak metadata."""

        base_columns = fighter_summary_columns()
        load_columns, supports_was_interim = await self._resolve_fighter_columns(
            base_columns
        )

        query = (
            select(Fighter)
            .options(load_only(*load_columns))
            .order_by(
                Fighter.last_fight_date.desc().nulls_last(),
                Fighter.name,
                Fighter.id,
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
            fight_status_by_fighter = await fetch_fight_status(
                self._session, fighter_ids
            )

        ranking_summaries = (
            await fetch_ranking_summaries(self._session, fighter_ids)
            if fighters
            else {}
        )

        today_utc: date = datetime.now(tz=UTC).date()

        roster_entries: list[FighterListItem] = []
        for fighter in fighters:
            streak_bundle = streak_by_fighter.get(fighter.id, {})
            fight_status = fight_status_by_fighter.get(fighter.id, {})
            ranking = ranking_summaries.get(fighter.id)
            roster_entries.append(
                FighterListItem(
                    fighter_id=fighter.id,
                    detail_url=_fighter_detail_url(fighter.id),
                    name=fighter.name,
                    nickname=fighter.nickname,
                    record=fighter.record,
                    division=fighter.division,
                    height=fighter.height,
                    weight=fighter.weight,
                    reach=fighter.reach,
                    stance=fighter.stance,
                    dob=fighter.dob,
                    image_url=resolve_fighter_image(fighter.id, fighter.image_url),
                    age=_calculate_age(
                        dob=fighter.dob,
                        reference_date=today_utc,
                    ),
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
    ) -> tuple[list[FighterListItem], int]:
        """Search fighters by name, stance, division, champion status, or streak."""

        filters: list[Any] = []
        from backend.db.repositories.fighter.filters import normalize_search_filters

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

        base_columns = fighter_summary_columns()
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
            await fetch_ranking_summaries(self._session, fighter_ids)
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

        roster_entries: list[FighterListItem] = []
        for fighter in fighters:
            fight_status = fight_status_by_fighter.get(fighter.id, {})
            ranking = ranking_summaries.get(fighter.id)
            roster_entries.append(
                FighterListItem(
                    fighter_id=fighter.id,
                    detail_url=_fighter_detail_url(fighter.id),
                    name=fighter.name,
                    nickname=fighter.nickname,
                    record=fighter.record,
                    division=fighter.division,
                    height=fighter.height,
                    weight=fighter.weight,
                    reach=fighter.reach,
                    stance=fighter.stance,
                    dob=fighter.dob,
                    image_url=resolve_fighter_image(fighter.id, fighter.image_url),
                    age=_calculate_age(
                        dob=fighter.dob,
                        reference_date=today_utc,
                    ),
                    is_current_champion=fighter.is_current_champion,
                    is_former_champion=fighter.is_former_champion,
                    was_interim=fighter.was_interim if supports_was_interim else False,
                    current_streak_type=(
                        (_validate_streak_type(fighter.current_streak_type) or "none")
                        if include_streak
                        else "none"
                    ),
                    current_streak_count=(
                        fighter.current_streak_count if include_streak else 0
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

        return (roster_entries, total)

    async def get_fighters_for_comparison(
        self, fighter_ids: Sequence[str]
    ) -> list[FighterComparisonEntry]:
        """Return stats snapshots for the requested fighters in the input order."""

        if not fighter_ids:
            return []

        ordered_ids: list[str] = []
        for fighter_id in fighter_ids:
            if fighter_id not in ordered_ids:
                ordered_ids.append(fighter_id)

        base_columns = fighter_comparison_columns()
        load_columns, supports_was_interim = await self._resolve_fighter_columns(
            base_columns
        )
        fighters_stmt = (
            select(Fighter)
            .options(load_only(*load_columns))
            .where(Fighter.id.in_(ordered_ids))
        )
        fighters_result = await self._session.execute(fighters_stmt)
        fighters = fighters_result.scalars().all()
        fighter_map = {fighter.id: fighter for fighter in fighters}

        today_utc: date = datetime.now(tz=UTC).date()

        stats_stmt = (
            select(
                fighter_stats.c.fighter_id,
                fighter_stats.c.category,
                fighter_stats.c.metric,
                fighter_stats.c.value,
            )
            .where(fighter_stats.c.fighter_id.in_(ordered_ids))
            .order_by(fighter_stats.c.fighter_id)
        )

        stats_result = await self._session.execute(stats_stmt)
        stats_by_fighter: dict[str, dict[str, dict[str, str]]] = {}
        for fighter_id, category, metric, value in stats_result.all():
            if fighter_id is None or metric is None or value is None:
                continue
            category_bucket = stats_by_fighter.setdefault(fighter_id, {})
            metric_bucket = category_bucket.setdefault(category or "misc", {})
            metric_bucket[metric] = value

        comparison: list[FighterComparisonEntry] = []
        for fighter_id in ordered_ids:
            fighter = fighter_map.get(fighter_id)
            if fighter is None:
                continue
            resolve_fighter_image(fighter_id, fighter.image_url)
            stats_map = stats_by_fighter.get(fighter_id, {})
            comparison.append(
                FighterComparisonEntry(
                    fighter_id=fighter_id,
                    name=fighter.name,
                    record=fighter.record,
                    division=fighter.division,
                    striking=stats_map.get("striking", {}),
                    grappling=stats_map.get("grappling", {}),
                    significant_strikes=stats_map.get("significant_strikes", {}),
                    takedown_stats=stats_map.get("takedown_stats", {}),
                    career=stats_map.get("career", {}),
                    age=_calculate_age(
                        dob=fighter.dob,
                        reference_date=today_utc,
                    ),
                    is_current_champion=fighter.is_current_champion,
                    is_former_champion=fighter.is_former_champion,
                    was_interim=(
                        fighter.was_interim if supports_was_interim else False
                    ),
                )
            )

        return comparison

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Fetch detailed fighter information with optimized fight history joins."""

        import time

        start_time = time.time()

        base_columns = fighter_detail_columns()
        load_columns, supports_was_interim = await self._resolve_fighter_columns(
            base_columns
        )
        fighter_query = (
            select(Fighter)
            .options(load_only(*load_columns))
            .where(Fighter.id == fighter_id)
        )
        fighter_result = await self._session.execute(fighter_query)
        fighter = fighter_result.scalar_one_or_none()

        if fighter is None:
            return None

        stats_map: dict[str, dict[str, str]] = {}

        primary_fights_cte = (
            select(
                Fight.id.label("fight_id"),
                Fight.event_name,
                Fight.event_date,
                Fight.opponent_id,
                Fight.opponent_name,
                Fight.result,
                Fight.method,
                Fight.round,
                Fight.time,
                Fight.fight_card_url,
                Fight.stats,
                literal(True).label("is_primary"),
                literal(None).label("inverted_opponent_id"),
            ).where(Fight.fighter_id == fighter_id)
        ).cte("primary_fights")

        opponent_fights_cte = (
            select(
                Fight.id.label("fight_id"),
                Fight.event_name,
                Fight.event_date,
                literal(None).label("opponent_id"),
                literal(None).label("opponent_name"),
                Fight.result,
                Fight.method,
                Fight.round,
                Fight.time,
                Fight.fight_card_url,
                Fight.stats,
                literal(False).label("is_primary"),
                Fight.fighter_id.label("inverted_opponent_id"),
            ).where(Fight.opponent_id == fighter_id)
        ).cte("opponent_fights")

        combined_query = select(primary_fights_cte).union_all(
            select(opponent_fights_cte)
        )

        all_fights_result = await self._session.execute(combined_query)
        all_fights_rows = all_fights_result.all()

        opponent_ids: set[str] = set()
        for row in all_fights_rows:
            if row.is_primary and row.opponent_id:
                opponent_ids.add(row.opponent_id)
            elif not row.is_primary and row.inverted_opponent_id:
                opponent_ids.add(row.inverted_opponent_id)

        opponent_lookup: dict[str, str] = {}
        if opponent_ids:
            opponent_rows = await self._session.execute(
                select(Fighter.id, Fighter.name).where(Fighter.id.in_(opponent_ids))
            )
            opponent_lookup = {row.id: row.name for row in opponent_rows.all()}

        fight_dict: dict[tuple[str, str | None, str], FightHistoryEntry] = {}

        for row in all_fights_rows:
            if row.is_primary:
                opponent_name = row.opponent_name or opponent_lookup.get(
                    row.opponent_id, "Unknown"
                )
                fight_key = create_fight_key(
                    row.event_name,
                    row.event_date,
                    row.opponent_id,
                    opponent_name,
                )
                new_entry = FightHistoryEntry(
                    fight_id=row.fight_id,
                    event_name=row.event_name,
                    event_date=row.event_date,
                    opponent=opponent_name,
                    opponent_id=row.opponent_id,
                    result=row.result,
                    method=row.method or "",
                    round=row.round,
                    time=row.time,
                    fight_card_url=row.fight_card_url,
                    stats=row.stats,
                )
                if fight_key not in fight_dict:
                    fight_dict[fight_key] = new_entry
                else:
                    if should_replace_fight(fight_dict[fight_key].result, row.result):
                        fight_dict[fight_key] = new_entry
            else:
                opponent_id = row.inverted_opponent_id
                opponent_name = opponent_lookup.get(opponent_id, "Unknown")
                fight_key = create_fight_key(
                    row.event_name,
                    row.event_date,
                    opponent_id,
                    opponent_name,
                )
                inverted_result = _invert_fight_result(row.result)
                new_entry = FightHistoryEntry(
                    fight_id=row.fight_id,
                    event_name=row.event_name,
                    event_date=row.event_date,
                    opponent=opponent_name,
                    opponent_id=opponent_id,
                    result=inverted_result,
                    method=row.method or "",
                    round=row.round,
                    time=row.time,
                    fight_card_url=row.fight_card_url,
                    stats=row.stats,
                )
                if fight_key not in fight_dict:
                    fight_dict[fight_key] = new_entry
                else:
                    if should_replace_fight(
                        fight_dict[fight_key].result, inverted_result
                    ):
                        fight_dict[fight_key] = new_entry

        fight_history: list[FightHistoryEntry] = list(fight_dict.values())
        fight_history = sort_fight_history(fight_history)

        query_time = time.time() - start_time
        if query_time > 0.1:
            logger.warning("Slow fighter query: %s took %.3fs", fighter_id, query_time)

        computed_record = fighter.record
        if not computed_record:
            computed_from_fights = compute_record_from_fights(fight_history)
            if computed_from_fights:
                computed_record = computed_from_fights

        today_utc: date = datetime.now(tz=UTC).date()
        fighter_age: int | None = _calculate_age(
            dob=fighter.dob,
            reference_date=today_utc,
        )

        summary = (await fetch_ranking_summaries(self._session, [fighter.id])).get(
            fighter.id
        )

        return FighterDetail(
            fighter_id=fighter.id,
            detail_url=_fighter_detail_url(fighter.id),
            name=fighter.name,
            nickname=fighter.nickname,
            height=fighter.height,
            weight=fighter.weight,
            reach=fighter.reach,
            stance=fighter.stance,
            dob=fighter.dob,
            image_url=resolve_fighter_image(fighter.id, fighter.image_url),
            record=computed_record,
            leg_reach=fighter.leg_reach,
            division=fighter.division,
            age=fighter_age,
            striking=stats_map.get("striking", {}),
            grappling=stats_map.get("grappling", {}),
            significant_strikes=stats_map.get("significant_strikes", {}),
            takedown_stats=stats_map.get("takedown_stats", {}),
            career=stats_map.get("career", {}),
            fight_history=fight_history,
            is_current_champion=fighter.is_current_champion,
            is_former_champion=fighter.is_former_champion,
            was_interim=fighter.was_interim if supports_was_interim else False,
            championship_history=fighter.championship_history or {},
            current_rank=summary.current_rank if summary else None,
            current_rank_date=summary.current_rank_date if summary else None,
            current_rank_division=summary.current_rank_division if summary else None,
            current_rank_source=summary.current_rank_source if summary else None,
            peak_rank=summary.peak_rank if summary else None,
            peak_rank_date=summary.peak_rank_date if summary else None,
            peak_rank_division=summary.peak_rank_division if summary else None,
            peak_rank_source=summary.peak_rank_source if summary else None,
            birthplace=fighter.birthplace,
            birthplace_city=fighter.birthplace_city,
            birthplace_country=fighter.birthplace_country,
            nationality=fighter.nationality,
            fighting_out_of=fighter.fighting_out_of,
            training_gym=fighter.training_gym,
            training_city=fighter.training_city,
            training_country=fighter.training_country,
        )

    async def get_random_fighter(self) -> FighterListItem | None:
        """Get a random fighter from the database."""

        base_columns = fighter_summary_columns()
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

        ranking = (await fetch_ranking_summaries(self._session, [fighter.id])).get(
            fighter.id
        )

        return FighterListItem(
            fighter_id=fighter.id,
            detail_url=_fighter_detail_url(fighter.id),
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


__all__ = ["FighterRosterMixin"]
