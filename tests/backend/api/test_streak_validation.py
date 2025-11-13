"""Tests for streak parameter validation."""

import os
import os
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from backend.schemas.fighter import PaginatedFightersResponse
from backend.services.search_service import get_search_service


POSTGRES_TEST_URL = "postgresql+psycopg://tester:secret@localhost/ufc"
os.environ.setdefault("DATABASE_URL", POSTGRES_TEST_URL)

from backend.main import app  # noqa: E402
import backend.main as backend_main  # noqa: E402


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Provide a FastAPI test client with database dependencies stubbed."""

    monkeypatch.setattr(
        backend_main, "get_database_type", lambda: "postgresql", raising=False
    )
    monkeypatch.setattr(
        backend_main,
        "get_database_url",
        lambda: POSTGRES_TEST_URL,
        raising=False,
    )
    monkeypatch.setattr(
        "backend.db.connection.get_database_type", lambda: "postgresql", raising=False
    )
    monkeypatch.setattr(
        "backend.db.connection.get_database_url",
        lambda: POSTGRES_TEST_URL,
        raising=False,
    )
    monkeypatch.setattr("backend.warmup.warmup_all", AsyncMock(), raising=False)
    monkeypatch.setattr("backend.cache.close_redis", AsyncMock(), raising=False)

    class _StubSearchService:
        async def search_fighters(
            self,
            *,
            limit: int,
            offset: int,
            **_: object,
        ) -> PaginatedFightersResponse:
            return PaginatedFightersResponse(
                fighters=[],
                count=0,
                total=0,
                limit=limit,
                offset=offset,
                has_more=False,
            )

    def _provide_stub_service() -> _StubSearchService:
        return _StubSearchService()

    app.dependency_overrides[get_search_service] = _provide_stub_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_search_service, None)


def test_min_streak_count_requires_streak_type(client: TestClient) -> None:
    """Test that min_streak_count without streak_type is rejected."""
    response = client.get("/search/?q=fighter&min_streak_count=3")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "streak_type" in detail.lower() and (
        "must be provided together" in detail.lower() or "required" in detail.lower()
    )


def test_streak_type_requires_min_streak_count(client: TestClient) -> None:
    """Test that streak_type without min_streak_count is rejected."""
    response = client.get("/search/?q=fighter&streak_type=win")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "min_streak_count" in detail.lower() and (
        "must be provided together" in detail.lower() or "required" in detail.lower()
    )


def test_both_streak_params_work_together(client: TestClient) -> None:
    """Test that both params together are accepted."""
    response = client.get("/search/?q=fighter&streak_type=win&min_streak_count=3")

    # Should succeed (200 if results found, or 200 with empty list if no results, but not 422)
    assert response.status_code == 200
