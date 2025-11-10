"""Pydantic DTOs backing advanced statistics API responses."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Final, Literal

from pydantic import BaseModel, Field

# Metric + bucket identifiers -----------------------------------------------------------------
# Keeping these literal unions centralised guarantees both the FastAPI request validation layer
# and our SQL repository remain in sync when new metrics become available. The identifiers
# intentionally mirror the fighter_stats.metric values where appropriate so we can reuse the
# strings directly inside SQL expressions without an additional translation layer.
StatsSummaryMetricId = Literal[
    "fighters_indexed",
    "avg_sig_strikes_accuracy_pct",
    "avg_takedown_accuracy_pct",
    "avg_submission_attempts",
    "avg_fight_duration_minutes",
    "max_win_streak",
]

LeaderboardMetricId = Literal[
    "sig_strikes_accuracy_pct",
    "avg_submissions",
]

TrendTimeBucket = Literal["month", "quarter", "year"]

# Canonical metric metadata used across the stack. The repository layer pulls the SQL metric
# identifiers from the dictionaries below while API route validators lean on the Literal types
# declared above.
SUMMARY_METRIC_LABELS: Final[dict[StatsSummaryMetricId, str]] = {
    "fighters_indexed": "Fighters Indexed",
    "avg_sig_strikes_accuracy_pct": "Avg. Sig. Strike Accuracy",
    "avg_takedown_accuracy_pct": "Avg. Takedown Accuracy",
    "avg_submission_attempts": "Avg. Submission Attempts",
    "avg_fight_duration_minutes": "Avg. Fight Duration",
    "max_win_streak": "Longest Win Streak",
}

SUMMARY_METRIC_DESCRIPTIONS: Final[dict[StatsSummaryMetricId, str]] = {
    "fighters_indexed": "Total number of UFC fighters ingested from UFCStats.",
    "avg_sig_strikes_accuracy_pct": "Average significant strike accuracy across the roster (%).",
    "avg_takedown_accuracy_pct": "Average takedown accuracy rate across all fighters (%).",
    "avg_submission_attempts": "Average submission attempts per fight recorded for the roster.",
    "avg_fight_duration_minutes": "Average fight duration (minutes) derived from recorded bouts.",
    "max_win_streak": "Longest recorded win streak observed within the indexed fights.",
}

LEADERBOARD_METRIC_DESCRIPTIONS: Final[dict[LeaderboardMetricId, str]] = {
    "sig_strikes_accuracy_pct": "Fighters with the highest significant strike accuracy",
    "avg_submissions": "Fighters with the most submission attempts per fight",
}


# Summary Stats Models -------------------------------------------------------------------------
class StatsSummaryMetric(BaseModel):
    """Individual metric displayed in the summary KPIs section."""

    id: StatsSummaryMetricId
    label: str
    value: float
    description: str | None = None


class StatsSummaryResponse(BaseModel):
    """Summary statistics response containing key performance indicators."""

    metrics: list[StatsSummaryMetric] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


# Leaderboard Models
class LeaderboardEntry(BaseModel):
    """Represents a single ranked fighter in a leaderboard view."""

    fighter_id: str
    fighter_name: str
    metric_value: float
    detail_url: str | None = None
    fight_count: int | None = Field(
        default=None,
        description="Number of UFC fights used to calculate this metric (data quality indicator)"
    )


class LeaderboardDefinition(BaseModel):
    """Container for leaderboard metadata and ranked entries for a metric."""

    metric_id: LeaderboardMetricId
    title: str
    description: str | None = None
    entries: list[LeaderboardEntry] = Field(default_factory=list)


class LeaderboardsResponse(BaseModel):
    """Envelope bundling all leaderboard segments for the stats endpoint."""

    leaderboards: list[LeaderboardDefinition] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


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
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


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
