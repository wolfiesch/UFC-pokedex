from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, computed_field


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
    first_event_name: str | None = None
    first_event_date: date | None = None
    last_event_name: str | None = None
    last_event_date: date | None = None
    result_breakdown: dict[str, dict[str, int]] = Field(default_factory=dict)


class FightGraphResponse(BaseModel):
    nodes: list[FightGraphNode] = Field(default_factory=list)
    links: list[FightGraphLink] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @computed_field  # type: ignore[misc]
    @property
    def edges(self) -> list[FightGraphLink]:
        """Alias for links to maintain compatibility with frontend."""
        return self.links
