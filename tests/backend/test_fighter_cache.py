from __future__ import annotations

from datetime import date

import pytest

from backend.cache import comparison_key, detail_key, list_key, search_key
from backend.db.repositories.fighter_repository import FighterSearchFilters
from backend.schemas.fighter import (
    FighterComparisonEntry,
    FighterDetail,
    FighterListItem,
    PaginatedFightersResponse,
)
from backend.services import fighter_cache


def _sample_list_item() -> FighterListItem:
    """Create a deterministic ``FighterListItem`` for serialisation tests."""

    return FighterListItem(
        fighter_id="cache-test",
        name="Cache Test",
        detail_url="https://example.com/fighters/cache-test",
        record="10-1-0",
        division="Lightweight",
    )


def test_fighter_list_cache_key_matches_backend_cache_helpers() -> None:
    """Ensure the list cache key helper delegates to ``backend.cache``."""

    expected = list_key(20, 0, nationality="BR", include_streak=True, streak_window=4)
    actual = fighter_cache.fighter_list_cache_key(
        limit=20,
        offset=0,
        nationality="BR",
        include_streak=True,
        streak_window=4,
    )
    assert actual == expected


@pytest.mark.parametrize(
    "limit, offset",
    [(None, 0), (10, None), (-1, 0), (10, -4)],
)
def test_fighter_list_cache_key_requires_valid_pagination(
    limit: int | None, offset: int | None
) -> None:
    """Invalid pagination inputs disable caching for fighter lists."""

    actual = fighter_cache.fighter_list_cache_key(
        limit=limit,
        offset=offset,
        nationality=None,
        include_streak=False,
        streak_window=6,
    )
    assert actual is None


def test_fighter_list_serialization_round_trip() -> None:
    """Serialise then deserialise list payloads to ensure type fidelity."""

    fighters = [_sample_list_item()]
    payload = fighter_cache.serialize_fighter_list(fighters)
    restored = fighter_cache.deserialize_fighter_list(payload)
    assert restored == fighters


def test_fighter_detail_helpers_align_with_cache_module() -> None:
    """Detail cache helpers should be thin wrappers around ``backend.cache``."""

    fighter = FighterDetail(
        fighter_id="cache-detail",
        detail_url="https://example.com/fighters/cache-detail",
        name="Cache Detail",
        nickname="Helper",
        height="6'0\"",
        weight="185 lbs",
        reach='75"',
        stance="Orthodox",
        dob=date(1990, 1, 1),
        record="12-2-0",
        striking={},
        grappling={},
        fight_history=[],
    )

    assert fighter_cache.fighter_detail_cache_key("cache-detail") == detail_key(
        "cache-detail"
    )
    payload = fighter_cache.serialize_fighter_detail(fighter)
    assert isinstance(payload, dict)
    restored = fighter_cache.deserialize_fighter_detail(payload)
    assert restored == fighter


def test_search_cache_key_and_serialization() -> None:
    """Search helpers should yield deterministic keys and stable payloads."""

    filters = FighterSearchFilters(
        query="nunes",
        stance="orthodox",
        division="featherweight",
        champion_statuses=("current",),
        streak_type="win",
        min_streak_count=3,
    )
    response = PaginatedFightersResponse(
        fighters=[_sample_list_item()],
        total=1,
        limit=10,
        offset=0,
        has_more=False,
    )

    expected_key = search_key(
        query="nunes",
        stance="orthodox",
        division="featherweight",
        champion_statuses="current",
        streak_type="win",
        min_streak_count=3,
        limit=10,
        offset=0,
    )
    assert (
        fighter_cache.fighter_search_cache_key(filters, limit=10, offset=0)
        == expected_key
    )
    payload = fighter_cache.serialize_fighter_search(response)
    restored = fighter_cache.deserialize_fighter_search(payload)
    assert restored == response


def test_comparison_cache_helpers_require_multiple_ids() -> None:
    """Comparison cache helpers should refuse to cache single fighters."""

    assert fighter_cache.fighter_comparison_cache_key(["solo"]) is None
    assert fighter_cache.fighter_comparison_cache_key(
        ["alpha", "beta"]
    ) == comparison_key(["alpha", "beta"])

    entries = [
        FighterComparisonEntry(fighter_id="alpha", name="Alpha"),
        FighterComparisonEntry(fighter_id="beta", name="Beta"),
    ]
    payload = fighter_cache.serialize_fighter_comparisons(entries)
    assert fighter_cache.deserialize_fighter_comparisons(payload) == entries


def test_deserializers_reject_unexpected_shapes() -> None:
    """The deserialisers should raise ``TypeError`` for invalid payloads."""

    with pytest.raises(TypeError):
        fighter_cache.deserialize_fighter_list({})
    with pytest.raises(TypeError):
        fighter_cache.deserialize_fighter_detail([])
    with pytest.raises(TypeError):
        fighter_cache.deserialize_fighter_search([])
    with pytest.raises(TypeError):
        fighter_cache.deserialize_fighter_comparisons({})
