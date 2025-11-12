"""Tests covering FastAPI serialization details for fighter endpoints."""

from __future__ import annotations

import sys
import types
from collections.abc import AsyncIterator, Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient


# Provide lightweight redis stubs before importing ``backend.main`` so that the
# module-level cache wiring does not attempt to import optional dependencies
# absent in the test environment.
class _StubRedisClient:
    """Redis client shim implementing the minimal async surface the cache expects."""

    @classmethod
    def from_url(cls, *_args: object, **_kwargs: object) -> _StubRedisClient:
        return cls()

    async def ping(self) -> bool:
        return True

    async def get(self, _key: str) -> None:
        return None

    async def set(self, _key: str, _value: str, *, ex: int | None = None) -> None:
        return None

    async def delete(self, *_keys: str) -> None:
        return None

    async def scan_iter(self, match: str | None = None) -> AsyncIterator[str]:
        if False and match is not None:
            yield match
        return

    async def aclose(self) -> None:
        return None


class _StubConnectionError(Exception):
    """Placeholder exception mirroring redis' connection error."""


redis_module = types.ModuleType("redis")
redis_asyncio_module = types.ModuleType("redis.asyncio")
redis_exceptions_module = types.ModuleType("redis.exceptions")
redis_asyncio_module.Redis = _StubRedisClient
redis_exceptions_module.ConnectionError = _StubConnectionError
redis_module.asyncio = redis_asyncio_module
sys.modules.setdefault("redis", redis_module)
sys.modules.setdefault("redis.asyncio", redis_asyncio_module)
sys.modules.setdefault("redis.exceptions", redis_exceptions_module)

# Import backend modules after the Redis stubs are registered to avoid optional dependency errors.
from backend.main import app  # noqa: E402
from backend.schemas.fighter import FighterDetail  # noqa: E402
from backend.services.dependencies import get_fighter_query_service  # noqa: E402


class StubFighterQueryService:
    """Lightweight stand-in exposing only the ``get_fighter`` contract."""

    def __init__(self, detail: FighterDetail) -> None:
        self._detail = detail

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Return the pre-configured fighter irrespective of the identifier."""

        return self._detail


@pytest.fixture
def override_fighter_service() -> Iterator[None]:
    """Temporarily replace the fighter service dependency with a deterministic stub."""

    fighter_detail = FighterDetail(
        fighter_id="fighter-age-check",
        detail_url="https://example.com/fighter-age-check",
        name="Serialization Subject",
        nickname="Tester",
        record="10-2-0",
        division="Lightweight",
        height="5'10\"",
        weight="155 lbs",
        reach='72"',
        stance="Orthodox",
        dob=date(1990, 6, 15),
        image_url="https://example.com/fighter-age-check.png",
        leg_reach='40"',
        age=34,
        striking={},
        grappling={},
        significant_strikes={},
        takedown_stats={},
        career={},
        fight_history=[],
    )
    stub_service = StubFighterQueryService(fighter_detail)

    async def dependency_override() -> StubFighterQueryService:
        return stub_service

    app.dependency_overrides[get_fighter_query_service] = dependency_override
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_fighter_query_service, None)


@pytest.fixture
def client(
    override_fighter_service: Iterator[None],
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    """Provide a ``TestClient`` configured with the stub fighter service."""

    class _StubConnection:
        async def __aenter__(self) -> _StubConnection:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def run_sync(self, _callable):
            return None

    class _StubEngine:
        def begin(self) -> _StubConnection:
            return _StubConnection()

    stub_engine = _StubEngine()
    import backend.main as backend_main

    monkeypatch.setattr(backend_main, "get_engine", lambda: stub_engine, raising=False)
    monkeypatch.setattr(
        backend_main, "get_database_type", lambda: "sqlite", raising=False
    )
    monkeypatch.setattr("backend.db.connection.get_engine", lambda: stub_engine)
    monkeypatch.setattr("backend.db.connection.get_database_type", lambda: "sqlite")

    with TestClient(app) as test_client:
        yield test_client


def test_fastapi_serialises_age_field(client: TestClient) -> None:
    """Ensure the JSON payload exposes the age computed by the repository layer."""

    response = client.get("/fighters/fighter-age-check")

    assert response.status_code == 200
    payload = response.json()
    assert payload["age"] == 34
    assert payload["fighter_id"] == "fighter-age-check"
