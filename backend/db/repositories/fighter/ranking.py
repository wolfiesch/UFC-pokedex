"""Ranking lookup helpers reused across fighter repository mixins."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import FighterRanking


@dataclass
class FighterRankingSummary:
    """Lightweight bundle of ranking metadata for a fighter."""

    current_rank: int | None = None
    current_rank_date: date | None = None
    current_rank_division: str | None = None
    current_rank_source: str | None = None
    peak_rank: int | None = None
    peak_rank_date: date | None = None
    peak_rank_division: str | None = None
    peak_rank_source: str | None = None


_DEFAULT_RANKING_SOURCE: str | None = (
    os.getenv("FIGHTER_RANKING_SOURCE")
    or os.getenv("DEFAULT_RANKING_SOURCE")
    or "fightmatrix"
)
_DEFAULT_RANKING_SOURCE = (_DEFAULT_RANKING_SOURCE or "").strip() or None


async def fetch_ranking_summaries(
    session: AsyncSession,
    fighter_ids: Sequence[str],
    *,
    ranking_source: str | None = None,
) -> dict[str, FighterRankingSummary]:
    """Lookup current and peak rankings for the provided fighters."""

    source = ranking_source or _DEFAULT_RANKING_SOURCE
    if not source:
        return {}

    deduped_ids = [fid for fid in dict.fromkeys(fighter_ids) if fid]
    if not deduped_ids:
        return {}

    current_subquery = (
        select(
            FighterRanking.fighter_id.label("fighter_id"),
            FighterRanking.rank.label("rank"),
            FighterRanking.rank_date.label("rank_date"),
            FighterRanking.division.label("division"),
            FighterRanking.source.label("source"),
            func.row_number()
            .over(
                partition_by=FighterRanking.fighter_id,
                order_by=FighterRanking.rank_date.desc(),
            )
            .label("row_number"),
        )
        .where(FighterRanking.fighter_id.in_(deduped_ids))
        .where(FighterRanking.source == source)
    ).subquery()

    current_rows = await session.execute(
        select(
            current_subquery.c.fighter_id,
            current_subquery.c.rank,
            current_subquery.c.rank_date,
            current_subquery.c.division,
            current_subquery.c.source,
        ).where(current_subquery.c.row_number == 1)
    )

    peak_subquery = (
        select(
            FighterRanking.fighter_id.label("fighter_id"),
            FighterRanking.rank.label("rank"),
            FighterRanking.rank_date.label("rank_date"),
            FighterRanking.division.label("division"),
            FighterRanking.source.label("source"),
            func.row_number()
            .over(
                partition_by=FighterRanking.fighter_id,
                order_by=(
                    FighterRanking.rank.asc(),
                    FighterRanking.rank_date.desc(),
                ),
            )
            .label("row_number"),
        )
        .where(FighterRanking.fighter_id.in_(deduped_ids))
        .where(FighterRanking.source == source)
        .where(FighterRanking.rank.isnot(None))
    ).subquery()

    peak_rows = await session.execute(
        select(
            peak_subquery.c.fighter_id,
            peak_subquery.c.rank,
            peak_subquery.c.rank_date,
            peak_subquery.c.division,
            peak_subquery.c.source,
        ).where(peak_subquery.c.row_number == 1)
    )

    summaries: dict[str, FighterRankingSummary] = {}

    for row in current_rows:
        summary = summaries.setdefault(row.fighter_id, FighterRankingSummary())
        summary.current_rank = row.rank
        summary.current_rank_date = row.rank_date
        summary.current_rank_division = row.division
        summary.current_rank_source = row.source

    for row in peak_rows:
        summary = summaries.setdefault(row.fighter_id, FighterRankingSummary())
        summary.peak_rank = row.rank
        summary.peak_rank_date = row.rank_date
        summary.peak_rank_division = row.division
        summary.peak_rank_source = row.source

    return summaries


__all__ = ["FighterRankingSummary", "fetch_ranking_summaries"]
