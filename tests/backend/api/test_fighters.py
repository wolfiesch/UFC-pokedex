from __future__ import annotations

import json
import sys
import types
from collections.abc import AsyncIterator, Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("sqlalchemy")
pytest.importorskip("pytest_asyncio")
pytest.importorskip("aiosqlite")

pytest_asyncio = pytest.importorskip("pytest_asyncio")


# Ensure Redis dependencies referenced by ``backend.main`` are stubbed before import.
class _StubRedisClient:
    """Minimal Redis client shim supporting the cache interactions under test."""

    @classmethod
    def from_url(cls, *_args: object, **_kwargs: object) -> "_StubRedisClient":
        return cls()

    async def ping(self) -> bool:  # pragma: no cover - deterministic stub
        return True

    async def get(self, _key: str) -> None:
        return None

    async def set(self, _key: str, _value: str, *, ex: int | None = None) -> None:
        return None

    async def delete(self, *_keys: str) -> None:
        return None

    async def scan_iter(self, match: str | None = None) -> AsyncIterator[str]:
        if False and match is not None:  # pragma: no cover - placeholder branch
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

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.db.models import Base, Fight, Fighter, fighter_stats
from backend.db.repositories import PostgreSQLFighterRepository
from backend.schemas.fighter import FighterDetail
from backend.services.fighter_service import get_fighter_service
from backend.main import app


class _StubFighterService:
    """Fighter service stand-in that always returns the prepared detail payload."""

    def __init__(self, detail: FighterDetail) -> None:
        self._detail = detail

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        return self._detail


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Provide an in-memory SQLite session for API regression exercises."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        if session.in_transaction():
            await session.rollback()

    await engine.dispose()


@pytest_asyncio.fixture
async def fighter_detail(session: AsyncSession) -> FighterDetail:
    """Persist a fighter, cached stats, and return the hydrated repository payload."""

    fighter = Fighter(
        id="api-breakdown",
        name="API Breakdown",
        record="5-1-0",
        division="Lightweight",
    )
    fight = Fight(
        id="api-fight-1",
        fighter_id=fighter.id,
        opponent_id="api-opponent",
        opponent_name="API Opponent",
        event_name="API Event",
        event_date=date(2024, 2, 1),
        result="W",
        method=None,
        round=None,
        time=None,
        fight_card_url=None,
        stats={},
    )

    session.add_all([fighter, fight])
    await session.flush()

    cached_payload = {
        "fight_id": fight.id,
        "event_name": "API Event",
        "event_date": "2024-02-01",
        "opponent": "API Opponent",
        "opponent_id": "api-opponent",
        "result": "W",
        "method": "Submission",
        "round": 1,
        "time": "03:45",
        "fight_card_url": "https://example.com/api-fight",
        "stats": {"sig_strikes": "77", "takedowns": "2"},
    }

    await session.execute(
        insert(fighter_stats),
        [
            {
                "fighter_id": fighter.id,
                "category": "fight_history",
                "metric": fight.id,
                "value": json.dumps(cached_payload, sort_keys=True),
            }
        ],
    )
    await session.commit()

    repository = PostgreSQLFighterRepository(session)
    detail = await repository.get_fighter(fighter.id)
    assert detail is not None
    assert detail.fight_history, "The repository should expose fight history entries."
    return detail


@pytest.fixture
def client(fighter_detail: FighterDetail) -> Iterator[TestClient]:
    """Return a TestClient whose fighter service emits the prepared detail payload."""

    stub_service = _StubFighterService(fighter_detail)

    async def dependency_override() -> _StubFighterService:
        return stub_service

    app.dependency_overrides[get_fighter_service] = dependency_override
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_fighter_service, None)


def test_fighter_endpoint_emits_fight_history_stats(client: TestClient) -> None:
    """The fighter detail endpoint should surface cached fight metrics in the payload."""

    response = client.get("/fighters/api-breakdown")
    assert response.status_code == 200
    payload = response.json()

    assert payload["fighter_id"] == "api-breakdown"
    assert payload["fight_history"], "Expected fight history entries in API response."
    history_entry = payload["fight_history"][0]
    assert history_entry["method"] == "Submission"
    assert history_entry["stats"]["sig_strikes"] == "77"
    assert history_entry["stats"]["takedowns"] == "2"
