"""Cache key builders and serialization helpers for the stats service."""

from __future__ import annotations

from datetime import date

from backend.schemas.stats import (
    LeaderboardMetricId,
    LeaderboardsResponse,
    StatsSummaryResponse,
    TrendsResponse,
    TrendTimeBucket,
)

# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def deserialize_summary(payload: object) -> StatsSummaryResponse:
    """Deserialize cached summary payload into a :class:`StatsSummaryResponse`."""

    if not isinstance(payload, dict):
        raise TypeError("Expected cached stats summary to be a mapping")
    return StatsSummaryResponse.model_validate(payload)


def deserialize_leaderboards(payload: object) -> LeaderboardsResponse:
    """Deserialize cached leaderboard payload into a :class:`LeaderboardsResponse`."""

    if not isinstance(payload, dict):
        raise TypeError("Expected cached leaderboards payload to be a mapping")
    return LeaderboardsResponse.model_validate(payload)


def deserialize_trends(payload: object) -> TrendsResponse:
    """Deserialize cached trends payload into a :class:`TrendsResponse`."""

    if not isinstance(payload, dict):
        raise TypeError("Expected cached trends payload to be a mapping")
    return TrendsResponse.model_validate(payload)


# ---------------------------------------------------------------------------
# Cache key builders
# ---------------------------------------------------------------------------


def leaderboard_cache_key(
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
    """Build a deterministic cache key for leaderboard requests."""

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


def trends_cache_key(
    *,
    start_date: date | None,
    end_date: date | None,
    time_bucket: TrendTimeBucket,
    streak_limit: int,
) -> str:
    """Build a deterministic cache key for trend requests."""

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


def country_stats_cache_key(*, group_by: str, min_fighters: int) -> str:
    """Build a cache key for country statistics requests."""

    return f"stats:countries:{group_by}:{min_fighters}"


def city_stats_cache_key(
    *, group_by: str, country: str | None, min_fighters: int
) -> str:
    """Build a cache key for city statistics requests."""

    country_token = country or "all"
    return f"stats:cities:{group_by}:{country_token}:{min_fighters}"


def gym_stats_cache_key(*, country: str | None, min_fighters: int, sort_by: str) -> str:
    """Build a cache key for gym statistics requests."""

    country_token = country or "all"
    return f"stats:gyms:{country_token}:{min_fighters}:{sort_by}"


__all__ = [
    "city_stats_cache_key",
    "country_stats_cache_key",
    "deserialize_leaderboards",
    "deserialize_summary",
    "deserialize_trends",
    "gym_stats_cache_key",
    "leaderboard_cache_key",
    "trends_cache_key",
]
