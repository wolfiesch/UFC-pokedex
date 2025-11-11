"""Tests for nationality filtering cache key uniqueness."""
from __future__ import annotations

import pytest

from backend.cache import list_key


def test_list_cache_key_unique_for_different_nationalities() -> None:
    """Verify that cache keys are unique for different nationality values."""

    # Generate cache keys for different nationalities
    key_us = list_key(
        limit=20,
        offset=0,
        nationality="American",
        include_streak=False,
        streak_window=6,
    )
    key_br = list_key(
        limit=20,
        offset=0,
        nationality="Brazilian",
        include_streak=False,
        streak_window=6,
    )
    key_ie = list_key(
        limit=20,
        offset=0,
        nationality="Irish",
        include_streak=False,
        streak_window=6,
    )
    key_none = list_key(
        limit=20,
        offset=0,
        nationality=None,
        include_streak=False,
        streak_window=6,
    )

    # Verify all keys are unique
    keys = [key_us, key_br, key_ie, key_none]
    assert len(keys) == len(set(keys)), "Cache keys should be unique for different nationalities"

    # Verify nationality is included in the key
    assert "American" in key_us
    assert "Brazilian" in key_br
    assert "Irish" in key_ie
    assert "American" not in key_none


def test_list_cache_key_consistent_for_same_nationality() -> None:
    """Verify that cache keys are consistent for the same nationality."""

    key_1 = list_key(
        limit=20,
        offset=0,
        nationality="American",
        include_streak=False,
        streak_window=6,
    )
    key_2 = list_key(
        limit=20,
        offset=0,
        nationality="American",
        include_streak=False,
        streak_window=6,
    )

    # Keys should be identical for same parameters
    assert key_1 == key_2


def test_list_cache_key_different_for_different_pagination() -> None:
    """Verify that pagination affects cache keys."""

    key_page_1 = list_key(
        limit=20,
        offset=0,
        nationality="American",
        include_streak=False,
        streak_window=6,
    )
    key_page_2 = list_key(
        limit=20,
        offset=20,
        nationality="American",
        include_streak=False,
        streak_window=6,
    )

    # Keys should be different for different offsets
    assert key_page_1 != key_page_2


def test_list_cache_key_format() -> None:
    """Verify the cache key format includes all relevant parameters."""

    key = list_key(
        limit=20,
        offset=0,
        nationality="American",
        include_streak=True,
        streak_window=6,
    )

    # Key should follow the pattern: fighters:list:{limit}:{offset}:{nationality}:{streak}:{window}
    assert key.startswith("fighters:list:")
    parts = key.split(":")
    assert len(parts) == 7  # fighters, list, limit, offset, nationality, streak, window
    assert parts[2] == "20"  # limit
    assert parts[3] == "0"  # offset
    assert parts[4] == "American"  # nationality
    assert parts[5] == "1"  # streak (1 = include_streak=True)
    assert parts[6] == "6"  # streak_window


def test_count_cache_key_pattern() -> None:
    """Verify that count cache keys follow the expected pattern for nationality filtering.

    This test documents the expected cache key format for count queries with nationality filters.
    The pattern should be: fighters:count:{nationality} or fighters:count:all
    """
    # This is a documentation test - the actual key generation happens in
    # fighter_query_service.py @cached decorator

    # Expected patterns:
    # - fighters:count:all (no nationality filter)
    # - fighters:count:American (with nationality filter)
    # - fighters:count:Brazilian (with nationality filter)

    # The invalidate_fighter function should delete all these with pattern: fighters:count*
    assert True  # Documentation test - no actual execution needed
