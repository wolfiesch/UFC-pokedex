"""Tests for streak parameter validation."""
import os
import pytest
from fastapi.testclient import TestClient


# Set to use SQLite for tests before importing app
os.environ["USE_SQLITE"] = "1"

from backend.main import app

client = TestClient(app)


def test_min_streak_count_requires_streak_type():
    """Test that min_streak_count without streak_type is rejected."""
    response = client.get("/search/?q=fighter&min_streak_count=3")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "streak_type" in detail.lower() and ("must be provided together" in detail.lower() or "required" in detail.lower())


def test_streak_type_requires_min_streak_count():
    """Test that streak_type without min_streak_count is rejected."""
    response = client.get("/search/?q=fighter&streak_type=win")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "min_streak_count" in detail.lower() and ("must be provided together" in detail.lower() or "required" in detail.lower())


def test_both_streak_params_work_together():
    """Test that both params together are accepted."""
    response = client.get("/search/?q=fighter&streak_type=win&min_streak_count=3")

    # Should succeed (200 if results found, or 200 with empty list if no results, but not 422)
    assert response.status_code == 200
