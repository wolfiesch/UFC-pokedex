"""Pydantic DTOs backing advanced statistics API responses."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class LeaderboardEntry(BaseModel):
    """Represents a single ranked fighter in a leaderboard view."""

    fighter_id: str
    fighter_name: str
    division: str | None = None
    metric: str
    value: float


class MetricLeaderboard(BaseModel):
    """Container for leaderboard metadata and ranked entries for a metric."""

    metric: str
    entries: list[LeaderboardEntry] = Field(default_factory=list)


class LeaderboardsResponse(BaseModel):
    """Envelope bundling all leaderboard segments for the stats endpoint."""

    accuracy: MetricLeaderboard
    submissions: MetricLeaderboard


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


class TrendsResponse(BaseModel):
    """Aggregated trends combining longest streaks and average fight durations."""

    longest_win_streaks: list[WinStreakSummary] = Field(default_factory=list)
    average_fight_durations: list[AverageFightDuration] = Field(default_factory=list)
