from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class FightGraphNode(BaseModel):
    fighter_id: str
    name: str
    division: str | None = None
    record: str | None = None
    image_url: str | None = None
    total_fights: int = 0
    latest_event_date: date | None = None


class FightGraphLink(BaseModel):
    source: str
    target: str
    fights: int
    last_event_name: str | None = None
    last_event_date: date | None = None
    result_breakdown: dict[str, dict[str, int]] = Field(default_factory=dict)


class FightGraphResponse(BaseModel):
    nodes: list[FightGraphNode] = Field(default_factory=list)
    links: list[FightGraphLink] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
