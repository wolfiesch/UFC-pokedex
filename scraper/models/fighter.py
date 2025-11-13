from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class FighterListItem(BaseModel):
    fighter_id: str
    detail_url: HttpUrl
    name: str
    nickname: str | None = None
    height: str | None = None
    weight: str | None = None
    division: str | None = None
    reach: str | None = None
    stance: str | None = None
    dob: date | None = None


class FightHistoryEntry(BaseModel):
    fight_id: str
    event_name: str | None = None
    event_date: date | None = None
    opponent: str
    opponent_id: str | None = None
    result: str | None = None
    method: str | None = None
    round: int | None = None
    time: str | None = None
    fight_card_url: HttpUrl | None = None
    stats: dict[str, Any] = Field(default_factory=dict)


class FighterDetail(FighterListItem):
    record: str | None = None
    leg_reach: str | None = None
    age: int | None = None
    # Geography fields
    birthplace: str | None = None
    nationality: str | None = None  # ISO 3166-1 alpha-2 code
    fighting_out_of: str | None = None
    striking: dict[str, Any] = Field(default_factory=dict)
    grappling: dict[str, Any] = Field(default_factory=dict)
    significant_strikes: dict[str, Any] = Field(default_factory=dict)
    takedown_stats: dict[str, Any] = Field(default_factory=dict)
    fight_history: list[FightHistoryEntry] = Field(default_factory=list)

    @field_validator("age", mode="before")
    @classmethod
    def _empty_string_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class SherdogFighterDetail(BaseModel):
    """Sherdog fighter detail data model.

    This model represents data scraped from Sherdog fighter profile pages.
    It includes normalized measurements (imperial) and raw metric values.
    """

    # Identifiers
    ufc_id: str = Field(description="UFC fighter ID from our database")
    sherdog_id: int = Field(description="Sherdog fighter ID")
    sherdog_url: HttpUrl = Field(description="Sherdog fighter profile URL")
    ufc_name: str = Field(description="Fighter name from UFC database")
    match_confidence: float = Field(description="Fuzzy match confidence score (0-100)")

    # Core stats (normalized to imperial)
    dob: str | None = Field(None, description="Date of birth (ISO format: YYYY-MM-DD)")
    dob_raw: str | None = Field(None, description="Raw DOB string from Sherdog")
    height: str | None = Field(None, description="Height in feet/inches (e.g., 6' 4\")")
    height_cm: float | None = Field(None, description="Height in centimeters")
    weight: str | None = Field(None, description="Weight in pounds (e.g., 185 lbs.)")
    weight_kg: float | None = Field(None, description="Weight in kilograms")
    reach: str | None = Field(None, description='Reach in inches (e.g., 84")')
    reach_cm: float | None = Field(None, description="Reach in centimeters")
    stance: str | None = Field(None, description="Fighting stance (Orthodox, Southpaw, etc.)")
    nationality: str | None = Field(
        None, description="ISO 3166-1 alpha-2 country code (e.g., US, BR, IE)"
    )

    # Metadata
    item_type: str = Field(default="sherdog_fighter_detail", description="Item type identifier")

    @field_validator("dob", mode="before")
    @classmethod
    def _parse_dob(cls, value: Any) -> str | None:
        """Convert date to ISO string if needed."""
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @field_validator("match_confidence", mode="before")
    @classmethod
    def _validate_confidence(cls, value: Any) -> float:
        """Ensure confidence is between 0 and 100."""
        if value is None:
            return 0.0
        confidence = float(value)
        return max(0.0, min(100.0, confidence))


class FighterRankingItem(BaseModel):
    """Fighter ranking data from various sources (UFC, Fight Matrix, etc.).

    This model represents a single fighter's ranking snapshot at a specific date.
    It includes rank position, division, movement indicators, and metadata.
    """

    # Fighter identification
    fighter_name: str = Field(description="Fighter name from rankings source")
    fighter_id: str | None = Field(
        None, description="Matched fighter UUID (populated after name matching)"
    )
    match_confidence: float | None = Field(None, description="Name match confidence score (0-100)")

    # Ranking data
    division: str = Field(description="Weight class (e.g., 'Lightweight')")
    rank: int | None = Field(
        None, description="Rank position: 0=Champion, 1-15=Ranked, None=Not Ranked (NR)"
    )
    previous_rank: int | None = Field(None, description="Previous rank for movement tracking")
    is_interim: bool = Field(default=False, description="Whether this is an interim championship")

    # Metadata
    rank_date: date = Field(description="Date of this ranking snapshot")
    source: Literal["ufc", "fightmatrix", "tapology"] = Field(description="Ranking source")
    scrape_timestamp: date | None = Field(None, description="Timestamp when data was scraped")
    item_type: str = Field(
        default="fighter_ranking", description="Item type identifier for pipeline routing"
    )

    @field_validator("rank", mode="before")
    @classmethod
    def _parse_rank(cls, value: Any) -> int | None:
        """Parse rank from various formats."""
        if value is None or value == "NR" or value == "":
            return None

        # Handle "C" for champion
        if isinstance(value, str) and value.upper() == "C":
            return 0

        # Try to parse as integer
        try:
            rank_int = int(value)
            # Validate range
            if rank_int < 0 or rank_int > 15:
                return None
            return rank_int
        except (ValueError, TypeError):
            return None

    @field_validator("match_confidence", mode="before")
    @classmethod
    def _validate_match_confidence(cls, value: Any) -> float | None:
        """Ensure confidence is between 0 and 100."""
        if value is None:
            return None
        confidence = float(value)
        return max(0.0, min(100.0, confidence))
