"""Ranking enrichment helpers shared by fighter-facing repositories.

This module isolates the ranking lookups that decorate fighter payloads with
current and peak metadata. The helper functions remain intentionally pure (they
only depend on the provided SQLAlchemy session) so calling sites can keep their
own responsibilities focused on the data they load.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import FighterRanking

DEFAULT_RANKING_SOURCE = (
    os.getenv("FIGHTER_RANKING_SOURCE")
    or os.getenv("DEFAULT_RANKING_SOURCE")
    or "fightmatrix"
)
DEFAULT_RANKING_SOURCE = (DEFAULT_RANKING_SOURCE or "").strip() or None


@dataclass(slots=True)
class FighterRankingSummary:
    """Lightweight bundle of ranking metadata for a single fighter.

    The dataclass mirrors the public fields surfaced by the API schemas so that
    repositories can merge the information into their responses without knowing
    about the transport layer. ``slots=True`` keeps the object compact because
    it is frequently materialised for whole roster slices.
    """

    current_rank: int | None = None
    current_rank_date: date | None = None
    current_rank_division: str | None = None
    current_rank_source: str | None = None
    peak_rank: int | None = None
    peak_rank_date: date | None = None
    peak_rank_division: str | None = None
    peak_rank_source: str | None = None


async def fetch_ranking_summaries(
    session: AsyncSession,
    fighter_ids: Sequence[str],
    *,
    ranking_source: str | None,
) -> dict[str, FighterRankingSummary]:
    """Return current and peak ranking summaries for ``fighter_ids``.

    Args:
        session: Async SQLAlchemy session used to execute read queries.
        fighter_ids: Ordered sequence of fighter IDs to enrich.
        ranking_source: External ranking provider identifier to scope the
            lookups. ``None`` short-circuits the query entirely.

    Returns:
        Mapping of ``fighter_id`` to :class:`FighterRankingSummary` instances.
        The dictionary is empty if no ranking source was supplied.
    """

    if not ranking_source:
        # When no source is configured we avoid hitting the database entirely to
        # keep the repository responsive.
        return {}

    deduped_ids = [
        fighter_id for fighter_id in dict.fromkeys(fighter_ids) if fighter_id
    ]
    if not deduped_ids:
        return {}

    # Latest ranking snapshot per fighter for the configured source. ``row_number``
    # allows us to keep the query in SQL instead of filtering in Python.
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
        .where(FighterRanking.source == ranking_source)
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

    # Best (lowest numeric) rank ever achieved for the configured source.
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
        .where(FighterRanking.source == ranking_source)
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
