from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class FightHistoryEntry(BaseModel):
    fight_id: str
    event_name: str
    event_date: date | None = None
    opponent: str
    opponent_id: str | None = None
    result: str
    method: str
    round: int | None = None
    time: str | None = None
    fight_card_url: HttpUrl | None = None
    stats: dict[str, Any] = Field(default_factory=dict)


class FighterListItem(BaseModel):
    fighter_id: str
    detail_url: HttpUrl
    name: str
    nickname: str | None = None
    division: str | None = None
    height: str | None = None
    weight: str | None = None
    reach: str | None = None
    stance: str | None = None
    dob: date | None = None


class FighterDetail(FighterListItem):
    record: str | None = None
    leg_reach: str | None = None
    age: int | None = None
    striking: dict[str, Any] = Field(default_factory=dict)
    grappling: dict[str, Any] = Field(default_factory=dict)
    significant_strikes: dict[str, Any] = Field(default_factory=dict)
    takedown_stats: dict[str, Any] = Field(default_factory=dict)
    fight_history: list[FightHistoryEntry] = Field(default_factory=list)


class PaginatedFightersResponse(BaseModel):
    fighters: list[FighterListItem]
    total: int
    limit: int
    offset: int
    has_more: bool
