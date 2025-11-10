from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock

import pytest

from backend.schemas.ranking import (
    CurrentRankingsResponse,
    DivisionRankDate,
    RankingEntry,
)
from backend.services.ranking_service import RankingService


class _StubRankingRepository:
    """Minimal stub that mimics the repository contract for service tests."""

    def __init__(self, *, divisions: list[str], latest_date: date | None) -> None:
        self._divisions = divisions
        self._latest_date = latest_date

    async def get_all_divisions(self, source: str) -> list[str]:  # pragma: no cover - exercised in tests
        return self._divisions

    async def get_latest_ranking_date(self, source: str) -> date | None:  # pragma: no cover - exercised in tests
        return self._latest_date


def _build_service_stub(repo: _StubRankingRepository) -> RankingService:
    """Return a RankingService instance whose repository is replaced with ``repo``."""

    service: RankingService = RankingService.__new__(RankingService)  # type: ignore[call-arg]
    service.repository = repo  # type: ignore[attr-defined]
    return service


def _division_response(division: str, snapshot: date, *, fighters: int) -> CurrentRankingsResponse:
    entry = RankingEntry(
        ranking_id=f"{division}-rank",
        fighter_id=f"{division}-fighter",
        fighter_name=f"{division} Champ",
        nickname=None,
        rank=1,
        previous_rank=2,
        rank_movement=1,
        is_interim=False,
    )
    return CurrentRankingsResponse(
        division=division,
        source="ufc",
        rank_date=snapshot,
        rankings=[entry] * fighters,
        total_fighters=fighters,
    )


@pytest.mark.asyncio
async def test_get_all_rankings_includes_per_division_rank_dates() -> None:
    divisions = ["Flyweight", "Bantamweight"]
    repo = _StubRankingRepository(divisions=divisions, latest_date=date(2024, 6, 1))
    service = _build_service_stub(repo)

    flyweight = _division_response("Flyweight", date(2024, 5, 15), fighters=2)
    bantamweight = _division_response("Bantamweight", date(2024, 4, 20), fighters=1)

    service.get_current_rankings = AsyncMock(  # type: ignore[attr-defined]
        side_effect=[flyweight, bantamweight]
    )

    response = await RankingService.get_all_rankings(service, source="ufc")

    assert response.total_divisions == 2
    assert response.total_fighters == 3
    assert [model.model_dump() for model in response.division_rank_dates] == [
        DivisionRankDate(division="Flyweight", rank_date=date(2024, 5, 15)).model_dump(),
        DivisionRankDate(division="Bantamweight", rank_date=date(2024, 4, 20)).model_dump(),
    ]
    assert response.divisions == [flyweight, bantamweight]


@pytest.mark.asyncio
async def test_get_all_rankings_short_circuits_when_no_snapshots() -> None:
    repo = _StubRankingRepository(divisions=[], latest_date=None)
    service = _build_service_stub(repo)
    service.get_current_rankings = AsyncMock()  # type: ignore[attr-defined]

    response = await RankingService.get_all_rankings(service, source="ufc")

    assert response.divisions == []
    assert response.division_rank_dates == []
    assert response.total_divisions == 0
    assert response.total_fighters == 0
    service.get_current_rankings.assert_not_called()
