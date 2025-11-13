from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class EventListItem(BaseModel):
    """Event from the events list page (UFCStats)"""

    event_id: str
    detail_url: HttpUrl
    name: str
    date: date
    location: str | None = None
    status: str  # 'upcoming' or 'completed'


class EventFight(BaseModel):
    """Individual fight in an event fight card"""

    fight_id: str | None = None
    fighter_1_id: str | None = None
    fighter_1_name: str
    fighter_2_id: str | None = None
    fighter_2_name: str
    weight_class: str | None = None
    result: str | None = None  # Empty for upcoming events
    method: str | None = None  # Empty for upcoming events
    round: int | None = None  # Empty for upcoming events
    time: str | None = None  # Empty for upcoming events
    fight_url: HttpUrl | None = None
    stats: dict[str, Any] = Field(default_factory=dict)


class EventDetail(EventListItem):
    """Detailed event information from event detail page (UFCStats)"""

    venue: str | None = None
    promotion: str = "UFC"
    fight_card: list[EventFight] = Field(default_factory=list)


class TapologyEnrichment(BaseModel):
    """Enrichment data from Tapology"""

    event_id: str  # UFCStats event ID for matching
    tapology_url: HttpUrl
    sherdog_url: HttpUrl | None = None
    venue: str | None = None
    broadcast: str | None = None
    fighter_rankings: dict[str, str] = Field(default_factory=dict)  # fighter_id -> ranking string
    cancellations: list[dict[str, Any]] = Field(default_factory=list)
