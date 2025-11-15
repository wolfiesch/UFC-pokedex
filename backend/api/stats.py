from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.schemas.stats import (
    CityStat,
    CityStatsResponse,
    DEFAULT_LEADERBOARD_METRICS,
    CountryStat,
    CountryStatsResponse,
    GymStat,
    GymStatsResponse,
    LeaderboardMetricId,
    LeaderboardsResponse,
    StatsSummaryResponse,
    TrendTimeBucket,
    TrendsResponse,
)
from backend.services.stats_service import StatsService, get_stats_service

router = APIRouter()


@router.get("/summary", response_model=StatsSummaryResponse)
async def stats_summary(
    service: StatsService = Depends(get_stats_service),
) -> StatsSummaryResponse:
    return await service.get_stats_summary()


@router.get("/leaderboards", response_model=LeaderboardsResponse)
async def stats_leaderboards(
    limit: int = Query(10, ge=1, le=100, description="Maximum entries per leaderboard."),
    offset: int = Query(0, ge=0, description="Pagination offset for leaderboard entries."),
    metrics: list[LeaderboardMetricId] = Query(
        default=list(DEFAULT_LEADERBOARD_METRICS),
        description="Repeated fighter_stats.metric identifiers to rank (comma-separated).",
    ),
    division: str | None = Query(
        None,
        description="Filter by weight division (e.g., 'Lightweight', 'Heavyweight').",
    ),
    min_fights: int = Query(
        5, ge=1, le=50, description="Minimum number of UFC fights required."
    ),
    start_date: date | None = Query(
        None, description="Optional inclusive lower bound on fight event dates."
    ),
    end_date: date | None = Query(
        None, description="Optional inclusive upper bound on fight event dates."
    ),
    service: StatsService = Depends(get_stats_service),
) -> LeaderboardsResponse:
    """Expose fighter leaderboards for the requested metrics with filtering."""

    return await service.get_leaderboards(
        limit=limit,
        offset=offset,
        metrics=metrics,
        division=division,
        min_fights=min_fights,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/trends", response_model=TrendsResponse)
async def stats_trends(
    start_date: date | None = Query(
        None, description="Optional inclusive lower bound on fight event dates."
    ),
    end_date: date | None = Query(
        None, description="Optional inclusive upper bound on fight event dates."
    ),
    time_bucket: Annotated[
        TrendTimeBucket,
        Query(description="Temporal grouping for average fight durations."),
    ] = "month",
    streak_limit: int = Query(
        5, ge=1, le=50, description="Maximum fighters returned for win streak trends."
    ),
    service: StatsService = Depends(get_stats_service),
) -> TrendsResponse:
    """Return historical streaks and fight duration aggregations for dashboards."""

    return await service.get_trends(
        start_date=start_date,
        end_date=end_date,
        time_bucket=time_bucket,
        streak_limit=streak_limit,
    )


@router.get("/countries", response_model=CountryStatsResponse)
async def get_country_stats(
    group_by: Annotated[
        str,
        Query(
            pattern="^(birthplace|training|nationality)$",
            description="Group by birthplace, training country, or nationality",
        ),
    ] = "birthplace",
    min_fighters: int = Query(1, ge=1, description="Minimum number of fighters"),
    service: StatsService = Depends(get_stats_service),
) -> CountryStatsResponse:
    """Get fighter count by country.

    Examples:
        /stats/countries?group_by=birthplace
        /stats/countries?group_by=nationality&min_fighters=10
    """
    return await service.get_country_stats(group_by=group_by, min_fighters=min_fighters)


@router.get("/cities", response_model=CityStatsResponse)
async def get_city_stats(
    group_by: Annotated[
        str,
        Query(
            pattern="^(birthplace|training)$",
            description="Group by birthplace or training city",
        ),
    ] = "training",
    country: str | None = Query(None, description="Filter by country"),
    min_fighters: int = Query(5, ge=1, description="Minimum number of fighters"),
    service: StatsService = Depends(get_stats_service),
) -> CityStatsResponse:
    """Get fighter count by city.

    Examples:
        /stats/cities?group_by=training&min_fighters=10
        /stats/cities?group_by=birthplace&country=United States
    """
    return await service.get_city_stats(
        group_by=group_by, country=country, min_fighters=min_fighters
    )


@router.get("/gyms", response_model=GymStatsResponse)
async def get_gym_stats(
    country: str | None = Query(None, description="Filter by country"),
    min_fighters: int = Query(5, ge=1, description="Minimum number of fighters"),
    sort_by: Annotated[
        str,
        Query(pattern="^(fighters|name)$", description="Sort by fighter count or gym name"),
    ] = "fighters",
    service: StatsService = Depends(get_stats_service),
) -> GymStatsResponse:
    """Get fighter count by training gym.

    Examples:
        /stats/gyms?min_fighters=10
        /stats/gyms?country=United States&sort_by=fighters
    """
    return await service.get_gym_stats(country=country, min_fighters=min_fighters, sort_by=sort_by)
