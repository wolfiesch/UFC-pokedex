"""Pydantic schemas describing betting odds payloads."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class ClosingRange(BaseModel):
    start: str | None = None
    end: str | None = None


class OddsTimeSeriesPoint(BaseModel):
    timestamp_ms: int = Field(..., description="Epoch timestamp (milliseconds).")
    timestamp: datetime = Field(..., description="ISO8601 timestamp for the sample.")
    odds: float = Field(..., description="Decimal odds value.")


class FighterOddsHistoryEntry(BaseModel):
    id: str
    opponent_name: str
    event_name: str
    event_date: date | None = None
    event_url: str | None = None
    opening_odds: str | None = None
    closing_range: ClosingRange | None = None
    num_odds_points: int
    data_quality: str


class FighterOddsHistoryResponse(BaseModel):
    fighter_id: str
    total_fights: int
    returned: int
    odds_history: list[FighterOddsHistoryEntry]


class FighterOddsChartFight(BaseModel):
    fight_id: str
    opponent: str
    event: str
    event_date: date | None = None
    event_url: str | None = None
    opening_odds: str | None = None
    closing_odds: str | None = None
    quality: str
    num_odds_points: int
    time_series: list[OddsTimeSeriesPoint]


class FighterOddsChartResponse(BaseModel):
    fighter_id: str
    fights: list[FighterOddsChartFight]


class FightOddsDetailResponse(BaseModel):
    id: str
    fighter_id: str
    opponent_name: str
    event_name: str
    event_date: date | None = None
    event_url: str | None = None
    opening_odds: str | None = None
    closing_range: ClosingRange | None = None
    mean_odds_history: list[OddsTimeSeriesPoint]
    num_odds_points: int
    data_quality: str
    scraped_at: datetime
    bfo_fighter_url: str | None = None


class OddsCoverageStats(BaseModel):
    fighters_with_odds: int
    total_fighters: int
    coverage_percentage: float


class OddsQualityStatsResponse(BaseModel):
    total_records: int
    unique_fighters: int
    avg_odds_points: float
    quality_distribution: dict[str, int]
    coverage_stats: OddsCoverageStats


__all__ = [
    "ClosingRange",
    "FighterOddsChartFight",
    "FighterOddsChartResponse",
    "FighterOddsHistoryEntry",
    "FighterOddsHistoryResponse",
    "FightOddsDetailResponse",
    "OddsCoverageStats",
    "OddsQualityStatsResponse",
    "OddsTimeSeriesPoint",
]
