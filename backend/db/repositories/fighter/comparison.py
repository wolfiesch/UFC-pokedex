"""Comparison view helpers for fighter repositories."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import load_only

from backend.db.models import Fighter, fighter_stats
from backend.db.repositories.base import _calculate_age
from backend.schemas.fighter import FighterComparisonEntry
from backend.services.image_resolver import resolve_fighter_image


class FighterComparisonMixin:
    """Hydrate comparison payloads for a set of fighters."""

    async def get_fighters_for_comparison(
        self, fighter_ids: Sequence[str]
    ) -> list[FighterComparisonEntry]:
        """Return stats snapshots for the requested fighters in the input order."""

        if not fighter_ids:
            return []

        # Use dict.fromkeys() for O(n) deduplication while preserving order
        ordered_ids = list(dict.fromkeys(fighter_ids))

        base_columns = self._fighter_comparison_columns()
        load_columns, supports_was_interim = await self._resolve_fighter_columns(base_columns)
        fighters_stmt = (
            select(Fighter).options(load_only(*load_columns)).where(Fighter.id.in_(ordered_ids))
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
                    was_interim=(fighter.was_interim if supports_was_interim else False),
                )
            )

        return comparison
