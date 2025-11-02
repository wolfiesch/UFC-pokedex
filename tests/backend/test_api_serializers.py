"""Tests exercising the Pydantic serializers that back the public API."""

from __future__ import annotations

from datetime import date
from typing import Any

from backend.schemas.fighter import (
    FighterDetail,
    FighterListItem,
    FightHistoryEntry,
    PaginatedFightersResponse,
)


def test_fight_history_entry_round_trips_dates() -> None:
    """The serializer should coerce primitive payloads into strong types."""
    payload: dict[str, Any] = {
        "fight_id": "fight-1",
        "event_name": "UFC 300",
        "event_date": "2024-04-13",
        "opponent": "Jane Doe",
        "opponent_id": "opponent-9",
        "result": "W",
        "method": "KO/TKO",
        "round": 2,
        "time": "02:15",
        "fight_card_url": "http://example.com/fight-1",
        "stats": {"sig_strikes": "50 of 80"},
    }

    entry = FightHistoryEntry.model_validate(payload)

    assert entry.event_date == date(2024, 4, 13)
    assert entry.stats == {"sig_strikes": "50 of 80"}


def test_fighter_detail_embeds_history_and_stats() -> None:
    """Ensure nested history objects survive the round trip through the schema."""
    fighter = FighterDetail(
        fighter_id="alpha-1",
        detail_url="http://ufcstats.com/fighter-details/alpha-1",
        name="Alpha One",
        nickname="The First",
        division="Lightweight",
        height="5' 9\"",
        weight="155 lbs.",
        reach='72"',
        stance="Orthodox",
        dob=date(1990, 1, 1),
        record="10-2-0",
        leg_reach='40"',
        age=34,
        striking={"sig_strikes_landed_per_min": 4.1},
        grappling={"takedown_average": 1.9},
        significant_strikes={"accuracy": "45%"},
        takedown_stats={"accuracy": "55%"},
        fight_history=[
            FightHistoryEntry(
                fight_id="fight-1",
                event_name="UFC 300",
                event_date=date(2024, 4, 13),
                opponent="Jane Doe",
                opponent_id="opponent-9",
                result="W",
                method="KO/TKO",
                round=2,
                time="02:15",
                fight_card_url="http://example.com/fight-1",
                stats={"sig_strikes": "50 of 80"},
            )
        ],
    )

    serialized = fighter.model_dump(mode="json")

    assert serialized["fighter_id"] == "alpha-1"
    assert serialized["fight_history"][0]["event_date"] == "2024-04-13"
    assert serialized["striking"]["sig_strikes_landed_per_min"] == 4.1


def test_paginated_fighters_response_metadata(
    leaderboard_payload: list[dict[str, Any]],
) -> None:
    """Pagination metadata exposes total counts used by the Stats Hub UI."""
    fighters = [
        FighterListItem(
            fighter_id=item["fighter_id"],
            detail_url=f"http://ufcstats.com/fighter-details/{item['fighter_id']}",
            name=item["fighter_name"],
        )
        for item in leaderboard_payload
    ]

    response = PaginatedFightersResponse(
        fighters=fighters,
        total=42,
        limit=3,
        offset=0,
        has_more=True,
    )

    assert response.total == 42
    assert len(response.fighters) == 3
    assert response.has_more is True
