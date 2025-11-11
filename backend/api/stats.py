from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.schemas.stats import (
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
    limit: int = Query(
        10, ge=1, le=100, description="Maximum entries per leaderboard."
    ),
    offset: int = Query(
        0, ge=0, description="Pagination offset for leaderboard entries."
    ),
    accuracy_metric: Annotated[
        LeaderboardMetricId,
        Query(description="fighter_stats.metric name representing accuracy to rank."),
    ] = "sig_strikes_accuracy_pct",
    submissions_metric: Annotated[
        LeaderboardMetricId,
        Query(
            description="fighter_stats.metric name representing submissions to rank."
        ),
    ] = "avg_submissions",
    division: str | None = Query(
        None,
        description="Filter by weight division (e.g., 'Lightweight', 'Heavyweight').",
    ),
    min_fights: int | None = Query(
        None, ge=1, le=50, description="Minimum number of UFC fights required."
    ),
    start_date: date | None = Query(
        None, description="Optional inclusive lower bound on fight event dates."
    ),
    end_date: date | None = Query(
        None, description="Optional inclusive upper bound on fight event dates."
    ),
    service: StatsService = Depends(get_stats_service),
) -> LeaderboardsResponse:
    """Expose fighter leaderboards for accuracy- and submission-oriented metrics with filtering."""

    return await service.get_leaderboards(
        limit=limit,
        offset=offset,
        accuracy_metric=accuracy_metric,
        submissions_metric=submissions_metric,
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
