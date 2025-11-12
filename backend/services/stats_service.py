"""Service exposing aggregate fighter statistics with layered caching."""

from __future__ import annotations

import logging
from datetime import date

from fastapi import Depends
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import CacheClient, get_cache_client
from backend.db.connection import get_db
from backend.db.repositories.fighter_repository import FighterRepository
from backend.db.repositories.stats_repository import StatsRepository
from backend.schemas.stats import (
    CityStatsResponse,
    CountryStatsResponse,
    GymStatsResponse,
    LeaderboardMetricId,
    LeaderboardsResponse,
    StatsSummaryResponse,
    TrendsResponse,
    TrendTimeBucket,
)
from backend.services.caching import CacheableService, cached
from backend.services.stats.cache_keys import (
    city_stats_cache_key,
    country_stats_cache_key,
    deserialize_leaderboards,
    deserialize_summary,
    deserialize_trends,
    gym_stats_cache_key,
    leaderboard_cache_key,
    trends_cache_key,
)
from backend.services.stats.location_stats_aggregator import (
    CityGroupBy,
    CountryGroupBy,
    GymSortBy,
    LocationStatsAggregator,
)

logger = logging.getLogger(__name__)


class StatsService(CacheableService):
    """Expose analytical statistics with shared caching helpers."""

    def __init__(
        self,
        repository: StatsRepository,
        location_aggregator: LocationStatsAggregator,
        *,
        cache: CacheClient | None = None,
    ) -> None:
        super().__init__(cache=cache)
        self._repository = repository
        # Delegate location-heavy aggregations to the dedicated collaborator so this
        # service remains focused on orchestrating cache lookups and repository calls.
        self._location_aggregator = location_aggregator

    @cached(
        lambda _self: "stats:summary",
        ttl=300,
        serializer=lambda summary: summary.model_dump(mode="json"),
        deserializer=deserialize_summary,
        deserialize_error_message=(
            "Failed to deserialize cached stats summary for key {key}: {error}"
        ),
    )
    async def get_stats_summary(self) -> StatsSummaryResponse:
        """Return dashboard friendly KPIs."""

        return await self._repository.stats_summary()

    @cached(
        lambda _self, **kwargs: leaderboard_cache_key(**kwargs),
        ttl=180,
        serializer=lambda response: response.model_dump(mode="json"),
        deserializer=deserialize_leaderboards,
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
        lambda _self, *, start_date, end_date, time_bucket, streak_limit: trends_cache_key(
            start_date=start_date,
            end_date=end_date,
            time_bucket=time_bucket,
            streak_limit=streak_limit,
        ),
        ttl=180,
        serializer=lambda response: response.model_dump(mode="json"),
        deserializer=deserialize_trends,
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

    @cached(
        lambda _self, *, group_by, min_fighters: country_stats_cache_key(
            group_by=group_by,
            min_fighters=min_fighters,
        ),
        ttl=600,
        serializer=lambda response: response.model_dump(mode="json"),
        deserializer=lambda payload: (
            CountryStatsResponse.model_validate(payload)
            if isinstance(payload, dict)
            else None
        ),
        deserialize_error_message=(
            "Failed to deserialize cached country stats for key {key}: {error}"
        ),
    )
    async def get_country_stats(
        self, *, group_by: CountryGroupBy, min_fighters: int
    ) -> CountryStatsResponse:
        """Get fighter count by country."""
        return await self._location_aggregator.get_country_stats(
            group_by=group_by,
            min_fighters=min_fighters,
        )

    @cached(
        lambda _self, *, group_by, country, min_fighters: city_stats_cache_key(
            group_by=group_by,
            country=country,
            min_fighters=min_fighters,
        ),
        ttl=600,
        serializer=lambda response: response.model_dump(mode="json"),
        deserializer=lambda payload: (
            CityStatsResponse.model_validate(payload)
            if isinstance(payload, dict)
            else None
        ),
        deserialize_error_message=(
            "Failed to deserialize cached city stats for key {key}: {error}"
        ),
    )
    async def get_city_stats(
        self, *, group_by: CityGroupBy, country: str | None, min_fighters: int
    ) -> CityStatsResponse:
        """Get fighter count by city."""
        return await self._location_aggregator.get_city_stats(
            group_by=group_by,
            country=country,
            min_fighters=min_fighters,
        )

    @cached(
        lambda _self, *, country, min_fighters, sort_by: gym_stats_cache_key(
            country=country,
            min_fighters=min_fighters,
            sort_by=sort_by,
        ),
        ttl=600,
        serializer=lambda response: response.model_dump(mode="json"),
        deserializer=lambda payload: (
            GymStatsResponse.model_validate(payload)
            if isinstance(payload, dict)
            else None
        ),
        deserialize_error_message=(
            "Failed to deserialize cached gym stats for key {key}: {error}"
        ),
    )
    async def get_gym_stats(
        self, *, country: str | None, min_fighters: int, sort_by: GymSortBy
    ) -> GymStatsResponse:
        """Get fighter count by gym."""
        return await self._location_aggregator.get_gym_stats(
            country=country,
            min_fighters=min_fighters,
            sort_by=sort_by,
        )


def get_stats_service(
    session: AsyncSession = Depends(get_db),
    cache: CacheClient = Depends(get_cache_client),
) -> StatsService:
    """FastAPI dependency wiring the stats repository and cache layer."""

    repository = StatsRepository(session)
    fighter_repository = FighterRepository(session)
    location_aggregator = LocationStatsAggregator(fighter_repository)
    return StatsService(
        repository,
        location_aggregator,
        cache=cache,
    )


__all__ = ["StatsService", "get_stats_service"]
