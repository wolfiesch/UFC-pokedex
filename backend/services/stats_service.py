"""Service exposing aggregate fighter statistics with layered caching."""

from __future__ import annotations

import logging
from datetime import date

from fastapi import Depends
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import CacheClient, get_cache_client
from backend.db.connection import get_db
from backend.db.repositories.stats_repository import StatsRepository
from backend.schemas.stats import (
    LeaderboardMetricId,
    LeaderboardsResponse,
    StatsSummaryResponse,
    TrendTimeBucket,
    TrendsResponse,
)
from backend.services.caching import CacheableService, cached

logger = logging.getLogger(__name__)


def _deserialize_summary(payload: object) -> StatsSummaryResponse:
    """Return a :class:`StatsSummaryResponse` from cached data."""

    if not isinstance(payload, dict):
        raise TypeError("Expected cached stats summary to be a mapping")
    return StatsSummaryResponse.model_validate(payload)


def _deserialize_leaderboards(payload: object) -> LeaderboardsResponse:
    """Return a :class:`LeaderboardsResponse` from cached data."""

    if not isinstance(payload, dict):
        raise TypeError("Expected cached leaderboards payload to be a mapping")
    return LeaderboardsResponse.model_validate(payload)


def _deserialize_trends(payload: object) -> TrendsResponse:
    """Return a :class:`TrendsResponse` from cached data."""

    if not isinstance(payload, dict):
        raise TypeError("Expected cached trends payload to be a mapping")
    return TrendsResponse.model_validate(payload)


def _leaderboard_cache_key(
    *,
    limit: int,
    offset: int,
    accuracy_metric: LeaderboardMetricId,
    submissions_metric: LeaderboardMetricId,
    division: str | None,
    min_fights: int | None,
    start_date: date | None,
    end_date: date | None,
) -> str:
    """Return a deterministic cache key for leaderboard requests."""

    return ":".join(
        [
            "stats",
            "leaderboards",
            str(limit),
            str(offset),
            accuracy_metric,
            submissions_metric,
            division or "*",
            str(min_fights) if min_fights is not None else "*",
            start_date.isoformat() if start_date else "*",
            end_date.isoformat() if end_date else "*",
        ]
    )


def _trends_cache_key(
    *,
    start_date: date | None,
    end_date: date | None,
    time_bucket: TrendTimeBucket,
    streak_limit: int,
) -> str:
    """Return a deterministic cache key for trend requests."""

    return ":".join(
        [
            "stats",
            "trends",
            start_date.isoformat() if start_date else "*",
            end_date.isoformat() if end_date else "*",
            time_bucket,
            str(streak_limit),
        ]
    )


class StatsService(CacheableService):
    """Expose analytical statistics with shared caching helpers."""

    def __init__(
        self,
        repository: StatsRepository,
        *,
        cache: CacheClient | None = None,
    ) -> None:
        super().__init__(cache=cache)
        self._repository = repository

    @cached(
        lambda _self: "stats:summary",
        ttl=300,
        serializer=lambda summary: summary.model_dump(mode="json"),
        deserializer=_deserialize_summary,
        deserialize_error_message=(
            "Failed to deserialize cached stats summary for key {key}: {error}"
        ),
    )
    async def get_stats_summary(self) -> StatsSummaryResponse:
        """Return dashboard friendly KPIs."""

        return await self._repository.stats_summary()

    @cached(
        lambda _self, *, limit, offset, accuracy_metric, submissions_metric, division, min_fights, start_date, end_date: _leaderboard_cache_key(
            limit=limit,
            offset=offset,
            accuracy_metric=accuracy_metric,
            submissions_metric=submissions_metric,
            division=division,
            min_fights=min_fights,
            start_date=start_date,
            end_date=end_date,
        ),
        ttl=180,
        serializer=lambda response: response.model_dump(mode="json"),
        deserializer=_deserialize_leaderboards,
        deserialize_error_message=(
            "Failed to deserialize cached leaderboards for key {key}: {error}"
        ),
    )
    async def get_leaderboards(
        self,
        *,
        limit: int,
        offset: int,
        accuracy_metric: LeaderboardMetricId,
        submissions_metric: LeaderboardMetricId,
        division: str | None,
        min_fights: int | None,
        start_date: date | None,
        end_date: date | None,
    ) -> LeaderboardsResponse:
        """Expose fighter leaderboards for accuracy- and submission-oriented metrics."""

        try:
            return await self._repository.get_leaderboards(
                limit=limit,
                offset=offset,
                accuracy_metric=accuracy_metric,
                submissions_metric=submissions_metric,
                division=division,
                min_fights=min_fights,
                start_date=start_date,
                end_date=end_date,
            )
        except ValidationError as exc:  # pragma: no cover - repository validation
            logger.warning("Failed to fetch leaderboards: %s", exc)
            raise

    @cached(
        lambda _self, *, start_date, end_date, time_bucket, streak_limit: _trends_cache_key(
            start_date=start_date,
            end_date=end_date,
            time_bucket=time_bucket,
            streak_limit=streak_limit,
        ),
        ttl=180,
        serializer=lambda response: response.model_dump(mode="json"),
        deserializer=_deserialize_trends,
        deserialize_error_message=(
            "Failed to deserialize cached trends for key {key}: {error}"
        ),
    )
    async def get_trends(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        time_bucket: TrendTimeBucket,
        streak_limit: int,
    ) -> TrendsResponse:
        """Provide historical streaks and fight duration trends for analytics dashboards."""

        return await self._repository.get_trends(
            start_date=start_date,
            end_date=end_date,
            time_bucket=time_bucket,
            streak_limit=streak_limit,
        )


def get_stats_service(
    session: AsyncSession = Depends(get_db),
    cache: CacheClient = Depends(get_cache_client),
) -> StatsService:
    """FastAPI dependency wiring the stats repository and cache layer."""

    repository = StatsRepository(session)
    return StatsService(repository, cache=cache)


__all__ = ["StatsService", "get_stats_service"]
