"""Repository encapsulating betting odds queries."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from backend.db.models import Fighter, FighterOdds

QUALITY_TIERS: tuple[str, ...] = ("excellent", "good", "usable", "poor", "no_data")
_QUALITY_TO_INDEX = {tier: index for index, tier in enumerate(QUALITY_TIERS)}


def _quality_filter(min_quality: str | None) -> Sequence[str] | None:
    if min_quality is None:
        return None

    normalized = min_quality.strip().lower()
    if normalized not in _QUALITY_TO_INDEX:
        raise ValueError(f"Unknown quality tier '{min_quality}'")

    max_index = _QUALITY_TO_INDEX[normalized]
    return QUALITY_TIERS[: max_index + 1]


class OddsRepository:
    """Provide typed odds queries for service consumption."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def fighter_exists(self, fighter_id: str) -> bool:
        stmt = select(func.count()).select_from(Fighter).where(Fighter.id == fighter_id)
        result = await self._session.execute(stmt)
        return bool(result.scalar_one())

    async def count_fighter_odds(
        self,
        fighter_id: str,
        *,
        min_quality: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(FighterOdds).where(
            FighterOdds.fighter_id == fighter_id
        )
        tier_values = _quality_filter(min_quality)
        if tier_values:
            stmt = stmt.where(FighterOdds.data_quality_tier.in_(tier_values))
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def list_fighter_odds(
        self,
        fighter_id: str,
        *,
        limit: int | None = None,
        min_quality: str | None = None,
    ) -> list[FighterOdds]:
        stmt: Select[Any] = (
            select(FighterOdds)
            .where(FighterOdds.fighter_id == fighter_id)
            .order_by(
                FighterOdds.event_date.desc().nullslast(),
                FighterOdds.scraped_at.desc(),
                FighterOdds.id.desc(),
            )
        )
        tier_values = _quality_filter(min_quality)
        if tier_values:
            stmt = stmt.where(FighterOdds.data_quality_tier.in_(tier_values))
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_odds_by_id(self, odds_id: str) -> FighterOdds | None:
        stmt = select(FighterOdds).where(FighterOdds.id == odds_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_quality_stats(self) -> dict[str, Any]:
        total_stmt = select(func.count()).select_from(FighterOdds)
        distinct_stmt = select(func.count(func.distinct(FighterOdds.fighter_id)))
        avg_stmt = select(func.avg(FighterOdds.num_odds_points))
        fighters_stmt = select(func.count()).select_from(Fighter)
        quality_stmt = (
            select(FighterOdds.data_quality_tier, func.count())
            .group_by(FighterOdds.data_quality_tier)
            .order_by(func.count().desc())
        )

        total = int((await self._session.execute(total_stmt)).scalar_one() or 0)
        unique_fighters = int(
            (await self._session.execute(distinct_stmt)).scalar_one() or 0
        )
        avg_points_value = (await self._session.execute(avg_stmt)).scalar_one()
        avg_points = float(avg_points_value or 0)
        total_fighters = int(
            (await self._session.execute(fighters_stmt)).scalar_one() or 0
        )

        quality_counts = {tier: 0 for tier in QUALITY_TIERS}
        quality_results = await self._session.execute(quality_stmt)
        for tier, count in quality_results.all():
            normalized = tier or "no_data"
            quality_counts[normalized] = int(count)

        coverage_percentage = (
            (unique_fighters / total_fighters) * 100 if total_fighters else 0.0
        )

        return {
            "total_records": total,
            "unique_fighters": unique_fighters,
            "avg_odds_points": avg_points,
            "quality_distribution": quality_counts,
            "coverage": {
                "fighters_with_odds": unique_fighters,
                "total_fighters": total_fighters,
                "coverage_percentage": coverage_percentage,
            },
        }


__all__ = ["OddsRepository", "QUALITY_TIERS"]
