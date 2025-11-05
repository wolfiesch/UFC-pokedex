"""Pydantic schemas that power the favorites API surface."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, validator


class FavoriteEntryBase(BaseModel):
    """Shared payload for favorite entry mutations."""

    fighter_id: str = Field(..., description="Primary key from the fighters table")
    position: int = Field(
        0,
        ge=0,
        description=(
            "Zero-based ordering index maintained by the drag-and-drop"
            " interactions on the dashboard."
        ),
    )
    notes: str | None = Field(
        None,
        max_length=1024,
        description="Optional scouting report written by the curator.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="User-defined labels that help cluster fighters.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary structured metadata persisted alongside the entry.",
    )

    @validator("tags", each_item=True)
    def _trim_tag(cls, value: str) -> str:
        """Normalize individual tag tokens so duplicates collapse."""

        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Tags must not be blank once whitespace is removed")
        return cleaned


class FavoriteEntryCreate(FavoriteEntryBase):
    """Payload for inserting a fighter into a collection."""

    pass


class FavoriteEntryUpdate(BaseModel):
    """Partial update payload for an existing entry."""

    position: int | None = Field(
        None,
        ge=0,
        description="New zero-based ordering index when drag-and-drop is used.",
    )
    notes: str | None = Field(None, max_length=1024)
    tags: list[str] | None = Field(None)
    metadata: dict[str, Any] | None = Field(None)

    @validator("tags")
    def _validate_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [token.strip() for token in value if token.strip()]
        if len(cleaned) != len(value):
            raise ValueError("Tags cannot be empty or whitespace-only")
        return cleaned


class FavoriteEntry(FavoriteEntryBase):
    """Read model exposed in API responses."""

    id: int = Field(..., description="Surrogate primary key for the entry row")
    created_at: datetime = Field(
        ..., description="Timestamp when the fighter was added to the collection."
    )
    updated_at: datetime = Field(..., description="Last mutation timestamp")

    class Config:
        orm_mode = True


class FavoriteCollectionBase(BaseModel):
    """Shared payload for collection-level operations."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1024)
    is_public: bool = Field(
        False,
        description="Flag that toggles visibility in the upcoming sharing flow.",
    )
    slug: str | None = Field(
        None,
        max_length=255,
        description="Optional stable slug used to build friendly URLs.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Key/value bag with future customization switches.",
    )


class FavoriteCollectionCreate(FavoriteCollectionBase):
    """Payload for creating a brand-new collection."""

    user_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Opaque identifier for the collection owner.",
    )


class FavoriteCollectionUpdate(BaseModel):
    """Partial update payload for a collection."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1024)
    is_public: bool | None = None
    slug: str | None = Field(None, max_length=255)
    metadata: dict[str, Any] | None = None


class FavoriteUpcomingFight(BaseModel):
    """Normalized summary describing an upcoming booked fight."""

    fighter_id: str
    opponent_name: str
    event_name: str
    event_date: date | None = Field(None, description="Scheduled date for the fight")
    weight_class: str | None = None


class FavoriteCollectionStats(BaseModel):
    """Aggregated statistics for a single collection."""

    total_fighters: int = Field(..., ge=0)
    win_rate: float = Field(..., ge=0.0, le=1.0)
    result_breakdown: dict[str, int] = Field(...)
    divisions: list[str] = Field(default_factory=list)
    upcoming_fights: list[FavoriteUpcomingFight] = Field(default_factory=list)


class FavoriteActivityItem(BaseModel):
    """Single entry in the activity feed timeline."""

    entry_id: int
    fighter_id: str
    action: str
    occurred_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class FavoriteCollectionSummary(FavoriteCollectionBase):
    """Lightweight representation used by listing endpoints."""

    id: int
    user_id: str
    created_at: datetime
    updated_at: datetime
    stats: FavoriteCollectionStats | None = None

    class Config:
        orm_mode = True


class FavoriteCollectionDetail(FavoriteCollectionSummary):
    """Full payload that includes entry information and activity feed."""

    entries: list[FavoriteEntry] = Field(default_factory=list)
    activity: list[FavoriteActivityItem] = Field(default_factory=list)


class FavoriteEntryReorderRequest(BaseModel):
    """Payload used by the drag-and-drop UI to persist ordering changes."""

    entry_ids: list[int] = Field(
        ...,
        description=(
            "Ordered list of entry identifiers representing the desired"
            " front-end arrangement."
        ),
    )


class FavoriteCollectionListResponse(BaseModel):
    """Container returned by the listing endpoint."""

    total: int
    collections: list[FavoriteCollectionSummary]
