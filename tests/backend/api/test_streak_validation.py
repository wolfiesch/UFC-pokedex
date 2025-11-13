"""Tests for streak parameter validation."""

import os
import os

import pytest
from fastapi.testclient import TestClient


# Provide a dummy PostgreSQL URL for application startup during tests.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://test_user:test_pass@localhost/test_db"
)

from backend.main import app
from backend.schemas.fighter import PaginatedFightersResponse
from backend.services.search_service import get_search_service


class _StubSearchService:
    """Return a deterministic empty result set for streak validation tests."""

    async def search_fighters(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        **_: object,
    ) -> PaginatedFightersResponse:
        effective_limit: int = limit if limit is not None else 20
        effective_offset: int = offset if offset is not None else 0
        return PaginatedFightersResponse(
            fighters=[],
            total=0,
            limit=effective_limit,
            offset=effective_offset,
            has_more=False,
        )


_STUB_SEARCH_SERVICE = _StubSearchService()
app.dependency_overrides[get_search_service] = lambda: _STUB_SEARCH_SERVICE

client = TestClient(app)


def test_min_streak_count_requires_streak_type():
    """Test that min_streak_count without streak_type is rejected."""
    response = client.get("/search/?q=fighter&min_streak_count=3")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "streak_type" in detail.lower() and (
        "must be provided together" in detail.lower() or "required" in detail.lower()
    )


def test_streak_type_requires_min_streak_count():
    """Test that streak_type without min_streak_count is rejected."""
    response = client.get("/search/?q=fighter&streak_type=win")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "min_streak_count" in detail.lower() and (
        "must be provided together" in detail.lower() or "required" in detail.lower()
    )


def test_both_streak_params_work_together():
    """Test that both params together are accepted."""
    response = client.get("/search/?q=fighter&streak_type=win&min_streak_count=3")

    # Should succeed (200 if results found, or 200 with empty list if no results, but not 422)
    assert response.status_code == 200
