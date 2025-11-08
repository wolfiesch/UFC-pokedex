from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, HttpUrl


class EventFight(BaseModel):
    """A fight in an event's fight card"""

    fight_id: str | None = None
    fighter_1_id: str | None = None
    fighter_1_name: str
    fighter_2_id: str | None = None
    fighter_2_name: str
    weight_class: str | None = None
    result: str | None = None
    method: str | None = None
    round: int | None = None
    time: str | None = None


class EventListItem(BaseModel):
    """Event summary for list views"""

    event_id: str
    name: str
    date: date
    location: str | None = None
    status: str  # 'upcoming' or 'completed'
    venue: str | None = None
    broadcast: str | None = None
    event_type: str | None = None  # 'ppv', 'fight_night', etc.


class EventDetail(EventListItem):
    """Detailed event information including fight card"""

    promotion: str = "UFC"
    ufcstats_url: HttpUrl | None = None
    tapology_url: HttpUrl | None = None
    sherdog_url: HttpUrl | None = None
    fight_card: list[EventFight] = Field(default_factory=list)


class PaginatedEventsResponse(BaseModel):
    """Paginated list of events"""

    events: list[EventListItem]
    total: int
    limit: int
    offset: int
    has_more: bool
