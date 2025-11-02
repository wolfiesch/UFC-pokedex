"""Integration-style tests that exercise FastAPI routes with a fake repository."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.schemas.fighter import FighterDetail, FighterListItem
from backend.services.fighter_service import (
    FighterRepositoryProtocol,
    FighterService,
    get_fighter_service,
)
from backend.services.search_service import SearchService, get_search_service


class FakeRepository(FighterRepositoryProtocol):
    """Simple in-memory repository used to drive deterministic API responses."""

    def __init__(
        self,
        fighters: list[FighterDetail],
        leaderboard: list[dict[str, Any]],
        trends: list[dict[str, Any]],
    ) -> None:
        self._fighters = fighters
        self._leaderboard = leaderboard
        self._trends = trends

    async def list_fighters(self, limit: int | None = None, offset: int | None = None):
        """Return paginated fighters with optional slicing."""
        slice_start = offset or 0
        slice_end = slice_start + limit if limit is not None else None
        return [
            FighterListItem(
                fighter_id=f.fighter_id,
                detail_url=f.detail_url,
                name=f.name,
                nickname=f.nickname,
                division=f.division,
                height=f.height,
                weight=f.weight,
                reach=f.reach,
                stance=f.stance,
                dob=f.dob,
            )
            for f in self._fighters[slice_start:slice_end]
        ]

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Fetch a fighter by identifier."""
        return next((f for f in self._fighters if f.fighter_id == fighter_id), None)

    async def stats_summary(self) -> dict[str, float]:
        """Aggregate simple metrics used by the Stats Hub visualizations."""
        total_fighters = float(len(self._fighters))
        max_accuracy = max((entry["value"] for entry in self._leaderboard), default=0.0)
        # Compute the most recent delta for the primary trend series
        latest_trend = self._trends[0]["points"]
        recent_delta = latest_trend[-1]["value"] - latest_trend[-2]["value"]
        return {
            "fighters_indexed": total_fighters,
            "best_striking_accuracy": max_accuracy,
            "recent_trend_delta": recent_delta,
        }

    async def count_fighters(self) -> int:
        """Expose a total count for pagination metadata."""
        return len(self._fighters)

    async def get_random_fighter(self) -> FighterListItem | None:
        """Return the first fighter to keep results deterministic for tests."""
        if not self._fighters:
            return None
        fighter = self._fighters[0]
        return FighterListItem(
            fighter_id=fighter.fighter_id,
            detail_url=fighter.detail_url,
            name=fighter.name,
            nickname=fighter.nickname,
            division=fighter.division,
            height=fighter.height,
            weight=fighter.weight,
            reach=fighter.reach,
            stance=fighter.stance,
            dob=fighter.dob,
        )

    async def search_fighters(
        self, query: str | None = None, stance: str | None = None
    ):  # pragma: no cover - exhaustively exercised via API calls
        """Filter fighters by substring match and stance constraints."""
        results = []
        for fighter in self._fighters:
            if query and query.lower() not in fighter.name.lower():
                continue
            if stance and (fighter.stance or "").lower() != stance.lower():
                continue
            results.append(
                FighterListItem(
                    fighter_id=fighter.fighter_id,
                    detail_url=fighter.detail_url,
                    name=fighter.name,
                    nickname=fighter.nickname,
                    division=fighter.division,
                    height=fighter.height,
                    weight=fighter.weight,
                    reach=fighter.reach,
                    stance=fighter.stance,
                    dob=fighter.dob,
                )
            )
        return results


@pytest_asyncio.fixture
async def api_client(
    leaderboard_payload: list[dict[str, Any]],
    trend_payload: list[dict[str, Any]],
) -> AsyncIterator[AsyncClient]:
    """Create an ``AsyncClient`` wired up with deterministic dependency overrides."""
    fighters = [
        FighterDetail(
            fighter_id="alpha-1",
            detail_url="http://ufcstats.com/fighter-details/alpha-1",
            name="Alpha One",
            nickname="The First",
            division="Lightweight",
            height="5' 9\"",
            weight="155 lbs.",
            reach='72"',
            stance="Orthodox",
            dob=None,
            record="10-2-0",
            leg_reach='40"',
            age=34,
            striking={"sig_strikes_landed_per_min": 4.1},
            grappling={"takedown_average": 1.9},
            significant_strikes={"accuracy": "45%"},
            takedown_stats={"accuracy": "55%"},
            fight_history=[],
        ),
        FighterDetail(
            fighter_id="bravo-2",
            detail_url="http://ufcstats.com/fighter-details/bravo-2",
            name="Bravo Two",
            nickname=None,
            division="Welterweight",
            height="5' 11\"",
            weight="170 lbs.",
            reach='74"',
            stance="Southpaw",
            dob=None,
            record="8-3-0",
            leg_reach=None,
            age=31,
            striking={"sig_strikes_landed_per_min": 3.7},
            grappling={"takedown_average": 2.1},
            significant_strikes={"accuracy": "41%"},
            takedown_stats={"accuracy": "48%"},
            fight_history=[],
        ),
    ]

    repository = FakeRepository(fighters, leaderboard_payload, trend_payload)
    service = FighterService(repository)

    def _override_fighter_service() -> FighterService:
        return service

    def _override_search_service() -> SearchService:
        return SearchService(service)

    app.dependency_overrides.clear()
    app.dependency_overrides[get_fighter_service] = _override_fighter_service
    app.dependency_overrides[get_search_service] = _override_search_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_fighters_returns_paginated_payload(api_client: AsyncClient) -> None:
    """Verify the `/fighters/` endpoint exposes pagination metadata."""
    response = await api_client.get("/fighters/?limit=1&offset=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["limit"] == 1
    assert payload["has_more"] is True


@pytest.mark.asyncio
async def test_get_fighter_returns_detail(api_client: AsyncClient) -> None:
    """Fetching a fighter by id should yield the enriched detail payload."""
    response = await api_client.get("/fighters/alpha-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["fighter_id"] == "alpha-1"
    assert payload["striking"]["sig_strikes_landed_per_min"] == 4.1


@pytest.mark.asyncio
async def test_get_random_fighter_is_deterministic(api_client: AsyncClient) -> None:
    """Random endpoint is pinned to the first fighter for reproducibility."""
    response = await api_client.get("/fighters/random")

    assert response.status_code == 200
    payload = response.json()
    assert payload["fighter_id"] == "alpha-1"


@pytest.mark.asyncio
async def test_search_endpoint_filters_by_query(api_client: AsyncClient) -> None:
    """Searching by partial name should return matching fighters only."""
    response = await api_client.get("/search/?q=Bravo")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["fighter_id"] == "bravo-2"


@pytest.mark.asyncio
async def test_stats_summary_exposes_leaderboard_metrics(
    api_client: AsyncClient,
) -> None:
    """Summary endpoint exposes metrics derived from leaderboard and trends fixtures."""
    response = await api_client.get("/stats/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "fighters_indexed": 2.0,
        "best_striking_accuracy": pytest.approx(0.64),
        "recent_trend_delta": pytest.approx(0.2999999999999998),
    }
