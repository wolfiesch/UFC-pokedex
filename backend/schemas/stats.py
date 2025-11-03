"""Pydantic DTOs backing advanced statistics API responses."""

from __future__ import annotations

from datetime import date, datetime, timezone

from pydantic import BaseModel, Field


# Summary Stats Models
class StatsSummaryMetric(BaseModel):
    """Individual metric displayed in the summary KPIs section."""

    id: str
    label: str
    value: float
    description: str | None = None


class StatsSummaryResponse(BaseModel):
    """Summary statistics response containing key performance indicators."""

    metrics: list[StatsSummaryMetric] = Field(default_factory=list)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# Leaderboard Models
class LeaderboardEntry(BaseModel):
    """Represents a single ranked fighter in a leaderboard view."""

    fighter_id: str
    fighter_name: str
    metric_value: float
    detail_url: str | None = None


class LeaderboardDefinition(BaseModel):
    """Container for leaderboard metadata and ranked entries for a metric."""

    metric_id: str
    title: str
    description: str | None = None
    entries: list[LeaderboardEntry] = Field(default_factory=list)


class LeaderboardsResponse(BaseModel):
    """Envelope bundling all leaderboard segments for the stats endpoint."""

    leaderboards: list[LeaderboardDefinition] = Field(default_factory=list)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def leaderboards_by_metric(self) -> dict[str, LeaderboardDefinition]:
        """Map metric identifiers to their corresponding leaderboard definitions."""

        return {leaderboard.metric_id: leaderboard for leaderboard in self.leaderboards}

    def get_leaderboard(self, metric_id: str) -> LeaderboardDefinition | None:
        """Return the leaderboard definition matching ``metric_id`` if present."""

        return self.leaderboards_by_metric.get(metric_id)


# Trend Models
class TrendPoint(BaseModel):
    """Data point used to render a trend line on the time-series chart."""

    timestamp: str
    value: float


class TrendSeries(BaseModel):
    """Series definition representing a tracked metric for a given entity."""

    metric_id: str
    fighter_id: str | None = None
    label: str
    points: list[TrendPoint] = Field(default_factory=list)


class TrendsResponse(BaseModel):
    """Aggregated trends combining time-series data for multiple metrics."""

    trends: list[TrendSeries] = Field(default_factory=list)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def win_streak_series(self) -> list[TrendSeries]:
        """Return trend series describing fighter win streak metrics."""

        return [series for series in self.trends if series.metric_id == "win_streak"]

    @property
    def average_duration_series(self) -> list[TrendSeries]:
        """Return trend series representing average fight durations by division."""

        return [
            series
            for series in self.trends
            if series.metric_id.startswith("avg_duration_")
        ]


# Internal/Helper Models (used by repository layer)
class WinStreakSummary(BaseModel):
    """A fighter's longest consecutive win streak within the filtered window."""

    fighter_id: str
    fighter_name: str
    division: str | None = None
    streak: int
    last_win_date: date | None = None


class AverageFightDuration(BaseModel):
    """Average bout duration for a division inside a temporal bucket."""

    division: str | None = None
    bucket_start: date
    bucket_label: str
    average_duration_seconds: float
    average_duration_minutes: float
