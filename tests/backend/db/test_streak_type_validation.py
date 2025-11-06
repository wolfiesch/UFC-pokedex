"""Tests for streak type validation."""
import pytest
from backend.db.models import Fighter


def test_streak_type_must_be_valid_literal():
    """Test that invalid streak types are rejected."""
    fighter = Fighter(
        id="test-id",
        name="Test Fighter",
        current_streak_count=5
    )

    # Valid values should work
    for valid_type in ["win", "loss", "draw", "none", None]:
        fighter.current_streak_type = valid_type  # Should not raise

    # Invalid value should raise or be caught
    with pytest.raises((ValueError, AssertionError)):
        fighter.current_streak_type = "invalid_type"
