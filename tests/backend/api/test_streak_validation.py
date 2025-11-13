"""Tests for streak parameter validation."""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.db.models import Base
from tests.backend.postgres import TemporaryPostgresSchema


@pytest.fixture()
def api_client(
    monkeypatch: pytest.MonkeyPatch,
    postgres_schema: TemporaryPostgresSchema,
) -> Iterator[TestClient]:
    """Provide a FastAPI ``TestClient`` bound to a temporary PostgreSQL schema."""

    postgres_schema.install_as_default(monkeypatch)

    async def _prepare_schema() -> None:
        async with postgres_schema.session_scope(Base.metadata):
            pass

    asyncio.run(_prepare_schema())

    db_connection = importlib.import_module("backend.db.connection")
    backend_main = importlib.import_module("backend.main")
    importlib.reload(db_connection)
    importlib.reload(backend_main)

    from backend.main import app

    with TestClient(app) as client:
        yield client

    # Dispose of the lazily created engine to avoid leaking connections.
    refreshed_connection = importlib.import_module("backend.db.connection")
    engine = getattr(refreshed_connection, "_engine", None)
    if engine is not None:
        asyncio.run(engine.dispose())
        refreshed_connection._engine = None
        refreshed_connection._session_factory = None


def test_min_streak_count_requires_streak_type(api_client: TestClient) -> None:
    """Test that min_streak_count without streak_type is rejected."""

    response = api_client.get("/search/?q=fighter&min_streak_count=3")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "streak_type" in detail.lower() and (
        "must be provided together" in detail.lower() or "required" in detail.lower()
    )


def test_streak_type_requires_min_streak_count(api_client: TestClient) -> None:
    """Test that streak_type without min_streak_count is rejected."""

    response = api_client.get("/search/?q=fighter&streak_type=win")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "min_streak_count" in detail.lower() and (
        "must be provided together" in detail.lower() or "required" in detail.lower()
    )


def test_both_streak_params_work_together(api_client: TestClient) -> None:
    """Test that both params together are accepted."""

    response = api_client.get("/search/?q=fighter&streak_type=win&min_streak_count=3")

    assert response.status_code == 200


def test_search_endpoint_without_trailing_slash(api_client: TestClient) -> None:
    """Ensure ``/search`` resolves so the frontend can omit the trailing slash."""

    response = api_client.get("/search?q=sample")

    assert response.status_code == 200
