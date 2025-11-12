"""Unit tests for the FavoritesAnalytics helper module."""

from datetime import UTC, datetime, timedelta

import pytest

from backend.db.models import FavoriteEntry, Fight, Fighter
from backend.schemas.favorites import FavoriteCollectionStats
from backend.services.favorites import FavoritesAnalytics


@pytest.fixture()
def analytics() -> FavoritesAnalytics:
    """Return a fresh analytics helper for each test."""

    return FavoritesAnalytics()


def _make_entry(
    *,
    entry_id: int,
    fighter_id: str,
    position: int,
    notes: str | None = None,
    tags: list[str] | None = None,
    added_offset: int = 0,
    updated_offset: int = 0,
) -> FavoriteEntry:
    """Create an in-memory FavoriteEntry with deterministic timestamps."""

    added_at = datetime(2024, 1, 1, tzinfo=UTC) + timedelta(days=added_offset)
    updated_at = added_at + timedelta(hours=updated_offset)
    entry = FavoriteEntry(
        id=entry_id,
        collection_id=1,
        fighter_id=fighter_id,
        position=position,
        notes=notes,
        tags=tags,
    )
    entry.added_at = added_at
    entry.updated_at = updated_at
    entry.fighter = Fighter(id=fighter_id, division="lightweight")
    return entry


def _make_fight(
    *,
    fighter_id: str,
    result: str,
    event_name: str,
) -> Fight:
    """Return a minimal Fight row usable by analytics tests."""

    fight = Fight(
        id=f"fight-{fighter_id}-{result}",
        fighter_id=fighter_id,
        opponent_name="Opponent",
        event_name=event_name,
        event_date=datetime(2024, 2, 1, tzinfo=UTC),
        weight_class="Lightweight",
        result=result,
    )
    return fight


def test_compute_collection_stats_with_mixed_results(
    analytics: FavoritesAnalytics,
) -> None:
    """The analytics helper should normalize fight results and compute win rates."""

    entries = [
        _make_entry(entry_id=1, fighter_id="101", position=1),
        _make_entry(entry_id=2, fighter_id="202", position=0),
    ]
    fights = [
        _make_fight(fighter_id="101", result="W", event_name="Fight Night 1"),
        _make_fight(fighter_id="101", result="L", event_name="Fight Night 2"),
        _make_fight(fighter_id="202", result="Next", event_name="Fight Night 3"),
    ]

    stats = analytics.compute_collection_stats(entries=entries, fights=fights)

    expected_breakdown = {
        "win": 1,
        "loss": 1,
        "draw": 0,
        "nc": 0,
        "upcoming": 1,
        "other": 0,
    }
    assert isinstance(stats, FavoriteCollectionStats)
    assert stats.total_fighters == 2
    assert pytest.approx(stats.win_rate, rel=1e-6) == 0.5
    assert stats.result_breakdown == expected_breakdown
    assert stats.divisions == ["lightweight"]
    assert len(stats.upcoming_fights) == 1
    assert stats.upcoming_fights[0].event_name == "Fight Night 3"


def test_activity_and_entry_serialization(analytics: FavoritesAnalytics) -> None:
    """Activity feed should reflect updates and entry schemas should be ordered."""

    entry_new = _make_entry(
        entry_id=1,
        fighter_id="303",
        position=1,
        notes="First note",
        tags=["prospect"],
        updated_offset=0,
    )
    entry_updated = _make_entry(
        entry_id=2,
        fighter_id="404",
        position=0,
        notes="Changed",
        tags=["veteran"],
        updated_offset=24,
    )

    activity = analytics.build_activity([entry_new, entry_updated])
    entries = analytics.entries_to_schema([entry_new, entry_updated])

    assert [item.entry_id for item in activity] == [2, 1]
    assert activity[0].action == "updated"
    assert entries[0].id == 2  # Ordered by position
    assert entries[1].metadata == {}
