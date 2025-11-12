"""Detailed fighter queries and comparison helpers."""

from __future__ import annotations

import time
from datetime import UTC, date, datetime
from typing import Any, Literal, cast

from sqlalchemy import literal, select, union_all
from sqlalchemy.orm import load_only

from backend.db.models import Fight, Fighter, fighter_stats
from backend.db.repositories.fight_utils import (
    compute_record_from_fights,
    create_fight_key,
    should_replace_fight,
    sort_fight_history,
)
from backend.services.image_resolver import resolve_fighter_image

from .logger import LOGGER
from .ranking import fetch_ranking_summaries


class FighterDetailMixin:
    """Mixin that handles detailed fighter lookups and comparisons."""

    async def get_fighter(self, fighter_id: str) -> "FighterDetail" | None:
        """Get detailed fighter information by ID with optimized single-query fetch."""

        start_time = time.time()

        base_columns = self._fighter_detail_columns()
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

        fight_dict: dict[str, Any] = {}
        for row in all_fights_result:
            opponent_id = row.opponent_id or row.inverted_opponent_id
            opponent_name = row.opponent_name
            if not opponent_name and opponent_id:
                opponent_query = select(Fighter.name).where(Fighter.id == opponent_id)
                opponent_result = await self._session.execute(opponent_query)
                opponent_name = opponent_result.scalar_one_or_none()

            result_value = row.result
            if not row.is_primary:
                result_value = self._invert_fight_result(result_value)

            fight_key = create_fight_key(row.event_name, row.fight_id)
            fight_entry = self._build_fight_history_entry(
                row=row,
                opponent_id=opponent_id,
                opponent_name=opponent_name,
                result_value=result_value,
            )

            if fight_key not in fight_dict:
                fight_dict[fight_key] = fight_entry
            elif should_replace_fight(fight_dict[fight_key].result, result_value):
                fight_dict[fight_key] = fight_entry

        fight_history = sort_fight_history(list(fight_dict.values()))

        query_time = time.time() - start_time
        if query_time > 0.1:
            LOGGER.warning("Slow fighter query: %s took %.3fs", fighter_id, query_time)

        computed_record = fighter.record
        if not computed_record:
            computed_from_fights = compute_record_from_fights(fight_history)
            if computed_from_fights:
                computed_record = computed_from_fights

        today_utc: date = datetime.now(tz=UTC).date()
        fighter_age: int | None = self._calculate_age(
            dob=fighter.dob,
            reference_date=today_utc,
        )

        summary = (
            await fetch_ranking_summaries(
                self._session, [fighter.id], ranking_source=self._ranking_source()
            )
        ).get(fighter.id)

        return self._build_fighter_detail(
            fighter=fighter,
            supports_was_interim=supports_was_interim,
            computed_record=computed_record,
            stats_map=stats_map,
            fight_history=fight_history,
            fighter_age=fighter_age,
            ranking_summary=summary,
        )

    async def get_fighters_for_comparison(
        self, fighter_ids: list[str]
    ) -> list["FighterComparisonEntry"]:
        """Return a list of fighters enriched with stats for comparison cards."""

        if not fighter_ids:
            return []

        base_columns = self._fighter_comparison_columns()
        load_columns, supports_was_interim = await self._resolve_fighter_columns(
            base_columns
        )
        stmt = (
            select(Fighter)
            .options(load_only(*load_columns))
            .where(Fighter.id.in_(fighter_ids))
        )
        fighters = (await self._session.execute(stmt)).scalars().all()
        fighter_map = {fighter.id: fighter for fighter in fighters}

        ordered_ids = [fid for fid in fighter_ids if fid in fighter_map]
        if not ordered_ids:
            return []

        stats_stmt = (
            select(
                fighter_stats.c.fighter_id,
                fighter_stats.c.category,
                fighter_stats.c.metric,
                fighter_stats.c.value,
            )
            .where(fighter_stats.c.fighter_id.in_(ordered_ids))
            .order_by(
                fighter_stats.c.fighter_id,
                fighter_stats.c.category,
                fighter_stats.c.metric,
            )
        )

        stats_result = await self._session.execute(stats_stmt)
        stats_by_fighter: dict[str, dict[str, dict[str, str]]] = {}
        for fighter_id, category, metric, value in stats_result.all():
            if fighter_id is None or metric is None or value is None:
                continue
            category_bucket = stats_by_fighter.setdefault(fighter_id, {})
            metric_bucket = category_bucket.setdefault(category or "misc", {})
            metric_bucket[metric] = value

        today_utc: date = datetime.now(tz=UTC).date()
        comparison: list["FighterComparisonEntry"] = []
        for fighter_id in ordered_ids:
            fighter = fighter_map.get(fighter_id)
            if fighter is None:
                continue
            resolve_fighter_image(fighter_id, fighter.image_url)
            stats_map = stats_by_fighter.get(fighter_id, {})
            comparison.append(
                self._build_comparison_entry(
                    fighter=fighter,
                    stats_map=stats_map,
                    supports_was_interim=supports_was_interim,
                    today_utc=today_utc,
                )
            )

        return comparison
