from __future__ import annotations

from datetime import date
from typing import Any

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
    reach: str | None = Field(None, description="Reach in inches (e.g., 84\")")
    reach_cm: float | None = Field(None, description="Reach in centimeters")
    stance: str | None = Field(None, description="Fighting stance (Orthodox, Southpaw, etc.)")
    nationality: str | None = Field(None, description="Fighter nationality")

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
