"""Shallow FastAPI tests covering the odds router wiring."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from backend.main import app
import backend.main as backend_main
from backend.schemas.odds import (
    ClosingRange,
    FighterOddsChartFight,
    FighterOddsChartResponse,
    FighterOddsHistoryEntry,
    FighterOddsHistoryResponse,
    FightOddsDetailResponse,
    OddsCoverageStats,
    OddsQualityStatsResponse,
    OddsTimeSeriesPoint,
)
from backend.services.dependencies import get_odds_query_service
from backend.services.odds_query_service import InvalidQualityTierError


class StubOddsQueryService:
    def __init__(self) -> None:
        self.history_response = FighterOddsHistoryResponse(
            fighter_id="fighter-1",
            total_fights=1,
            returned=1,
            odds_history=[
                FighterOddsHistoryEntry(
                    id="odds-1",
                    opponent_name="Opponent",
                    event_name="Event",
                    event_date=date(2024, 1, 1),
                    event_url="https://example.com/event",
                    opening_odds="+150",
                    closing_range=ClosingRange(start="+140", end="+130"),
                    num_odds_points=10,
                    data_quality="excellent",
                )
            ],
        )
        self.chart_response = FighterOddsChartResponse(
            fighter_id="fighter-1",
            fights=[
                FighterOddsChartFight(
                    fight_id="odds-1",
                    opponent="Opponent",
                    event="Event",
                    event_date=date(2024, 1, 1),
                    event_url="https://example.com/event",
                    opening_odds="+150",
                    closing_odds="+130",
                    quality="excellent",
                    num_odds_points=2,
                    time_series=[
                        OddsTimeSeriesPoint(
                            timestamp_ms=1,
                            timestamp=datetime(2024, 1, 1, 0, 0, 1),
                            odds=2.0,
                        )
                    ],
                )
            ],
        )
        self.detail_response = FightOddsDetailResponse(
            id="odds-1",
            fighter_id="fighter-1",
            opponent_name="Opponent",
            event_name="Event",
            event_date=date(2024, 1, 1),
            event_url="https://example.com/event",
            opening_odds="+150",
            closing_range=ClosingRange(start="+140", end="+130"),
            mean_odds_history=[
                OddsTimeSeriesPoint(
                    timestamp_ms=1, timestamp=datetime(2024, 1, 1, 0, 0, 1), odds=2.0
                )
            ],
            num_odds_points=1,
            data_quality="excellent",
            scraped_at=datetime(2024, 1, 1, 2, 0, 0),
            bfo_fighter_url="https://example.com/fighter",
        )
        self.stats_response = OddsQualityStatsResponse(
            total_records=1,
            unique_fighters=1,
            avg_odds_points=12.0,
            quality_distribution={"excellent": 1, "good": 0, "usable": 0, "poor": 0, "no_data": 0},
            coverage_stats=OddsCoverageStats(
                fighters_with_odds=1, total_fighters=1, coverage_percentage=100.0
            ),
        )
        self.raise_invalid = False
        self.return_none = False

    async def get_fighter_odds_history(
        self, fighter_id: str, *, limit: int = 100, min_quality: str | None = None
    ):
        if self.raise_invalid:
            raise InvalidQualityTierError("bad quality")
        if self.return_none:
            return None
        return self.history_response

    async def get_fighter_odds_chart(self, fighter_id: str, *, limit: int = 20):
        if self.return_none:
            return None
        return self.chart_response

    async def get_fight_odds_detail(self, odds_id: str):
        if self.return_none:
            return None
        return self.detail_response

    async def get_quality_stats(self):
        return self.stats_response


@pytest.fixture
def override_odds_service() -> Iterator[StubOddsQueryService]:
    service = StubOddsQueryService()

    async def dependency_override() -> StubOddsQueryService:
        return service

    app.dependency_overrides[get_odds_query_service] = dependency_override
    try:
        yield service
    finally:
        app.dependency_overrides.pop(get_odds_query_service, None)


@pytest.fixture
def client(
    override_odds_service: StubOddsQueryService,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    class _StubConnection:
        async def __aenter__(self) -> "_StubConnection":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def run_sync(self, _callable):
            return None

    class _StubEngine:
        def begin(self) -> _StubConnection:
            return _StubConnection()

    stub_engine = _StubEngine()
    monkeypatch.setattr(backend_main, "get_engine", lambda: stub_engine, raising=False)
    monkeypatch.setattr(
        backend_main, "get_database_type", lambda: "postgresql", raising=False
    )
    monkeypatch.setattr(
        backend_main, "get_database_url", lambda: "postgresql+psycopg://test:test@localhost/test"
    )
    monkeypatch.setattr("backend.db.connection.get_engine", lambda: stub_engine)
    monkeypatch.setattr("backend.db.connection.get_database_type", lambda: "postgresql")
    monkeypatch.setattr(
        "backend.db.connection.get_database_url",
        lambda: "postgresql+psycopg://test:test@localhost/test",
    )
    monkeypatch.setattr("backend.warmup.warmup_all", AsyncMock(), raising=False)
    monkeypatch.setattr("backend.cache.close_redis", AsyncMock(), raising=False)

    with TestClient(app) as test_client:
        yield test_client


def test_history_endpoint_returns_payload(
    client: TestClient, override_odds_service: StubOddsQueryService
) -> None:
    response = client.get("/odds/fighter/fighter-1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_fights"] == 1
    assert payload["odds_history"][0]["opponent_name"] == "Opponent"


def test_history_endpoint_handles_missing_fighter(
    client: TestClient, override_odds_service: StubOddsQueryService
) -> None:
    override_odds_service.return_none = True
    response = client.get("/odds/fighter/missing")
    assert response.status_code == 404


def test_history_endpoint_rejects_bad_quality(
    client: TestClient, override_odds_service: StubOddsQueryService
) -> None:
    override_odds_service.raise_invalid = True
    response = client.get("/odds/fighter/fighter-1?quality_min=ridiculous")
    assert response.status_code == 400


def test_chart_endpoint(client: TestClient) -> None:
    response = client.get("/odds/fighter/fighter-1/chart")
    assert response.status_code == 200
    assert response.json()["fights"][0]["closing_odds"] == "+130"


def test_fight_detail_endpoint(client: TestClient) -> None:
    response = client.get("/odds/fight/odds-1")
    assert response.status_code == 200
    assert response.json()["opponent_name"] == "Opponent"


def test_stats_endpoint(client: TestClient) -> None:
    response = client.get("/odds/stats/quality")
    assert response.status_code == 200
    assert response.json()["total_records"] == 1


# [*TO-DO*] - Add missing test coverage:
# 1. Test quality_min parameter with valid tiers (excellent, good, usable, poor)
# 2. Test pagination with limit > 500 (should reject with 400)
# 3. Test malformed fighter_id handling
# 4. Test edge cases for closing_range (one null, one set)
# 5. Test chart endpoint with missing fighter (404)
# 6. Test fight detail endpoint with missing odds_id (404)
