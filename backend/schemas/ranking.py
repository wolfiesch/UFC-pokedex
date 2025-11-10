"""Pydantic schemas for fighter rankings API responses."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class RankingEntry(BaseModel):
    """Single ranking entry within a division leaderboard."""

    ranking_id: str = Field(description="Unique ranking record ID")
    fighter_id: str = Field(description="Fighter's UUID")
    fighter_name: str = Field(description="Fighter's full name")
    nickname: str | None = Field(None, description="Fighter's nickname")
    rank: int | None = Field(
        description="Rank position: 0=Champion, 1-15=Ranked, null=Not Ranked (NR)"
    )
    previous_rank: int | None = Field(None, description="Previous rank position")
    rank_movement: int = Field(
        default=0,
        description="Rank movement delta (positive=moved up, negative=moved down)",
    )
    is_interim: bool = Field(
        default=False, description="Whether this is an interim championship"
    )


class CurrentRankingsResponse(BaseModel):
    """Current rankings for a specific division."""

    division: str = Field(description="Weight class (e.g., 'Lightweight')")
    source: str = Field(
        description="Ranking source: 'ufc', 'fightmatrix', 'tapology'"
    )
    rank_date: date = Field(description="Date of this ranking snapshot")
    rankings: list[RankingEntry] = Field(
        default_factory=list, description="List of ranked fighters"
    )
    total_fighters: int = Field(description="Total number of fighters in rankings")


class RankingHistoryEntry(BaseModel):
    """Single point in a fighter's ranking history timeline."""

    ranking_id: str = Field(description="Unique ranking record ID")
    division: str = Field(description="Weight class")
    rank: int | None = Field(
        description="Rank position: 0=Champion, 1-15=Ranked, null=Not Ranked"
    )
    previous_rank: int | None = Field(None, description="Previous rank")
    rank_movement: int = Field(default=0, description="Rank movement delta")
    is_interim: bool = Field(default=False, description="Interim championship flag")
    rank_date: date = Field(description="Date of this snapshot")
    source: str = Field(description="Ranking source")


class RankingHistoryResponse(BaseModel):
    """Historical ranking progression for a fighter."""

    fighter_id: str = Field(description="Fighter's UUID")
    fighter_name: str = Field(description="Fighter's full name")
    source: str = Field(description="Ranking source")
    history: list[RankingHistoryEntry] = Field(
        default_factory=list,
        description="Ranking snapshots ordered by date (most recent first)",
    )
    total_snapshots: int = Field(description="Total number of ranking snapshots")


class PeakRankingResponse(BaseModel):
    """Fighter's best ranking achievement."""

    fighter_id: str = Field(description="Fighter's UUID")
    fighter_name: str = Field(description="Fighter's full name")
    division: str = Field(description="Division where peak was achieved")
    peak_rank: int = Field(description="Best rank achieved (lower is better)")
    rank_date: date = Field(description="Date when peak rank was achieved")
    is_interim: bool = Field(default=False, description="Was this an interim title")
    source: str = Field(description="Ranking source")


class DivisionListResponse(BaseModel):
    """List of divisions with rankings available."""

    divisions: list[str] = Field(
        default_factory=list, description="Available division names"
    )
    source: str = Field(description="Ranking source")
    total_divisions: int = Field(description="Total number of divisions")


class AllRankingsResponse(BaseModel):
    """All current rankings across all divisions."""

    source: str = Field(description="Ranking source")
    rank_date: date = Field(description="Date of rankings snapshot")
    divisions: list[CurrentRankingsResponse] = Field(
        default_factory=list, description="Rankings for each division"
    )
    total_divisions: int = Field(description="Number of divisions included")
    total_fighters: int = Field(description="Total ranked fighters across all divisions")
