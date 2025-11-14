from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from backend.schemas.odds import (
    FighterOddsHistoryResponse,
    OddsQualityStatsResponse,
)
from backend.services.odds_query_service import (
    InvalidQualityTierError,
    OddsQueryService,
)


class StubRepository:
    def __init__(self) -> None:
        self.exists = True
        self.rows: list[SimpleNamespace] = []
        self.total = 0
        self.detail_row: SimpleNamespace | None = None
        self.stats_payload = {
            "total_records": 0,
            "unique_fighters": 0,
            "avg_odds_points": 0.0,
            "quality_distribution": {"excellent": 0, "good": 0, "usable": 0, "poor": 0, "no_data": 0},
            "coverage": {"fighters_with_odds": 0, "total_fighters": 0, "coverage_percentage": 0.0},
        }

    async def fighter_exists(self, fighter_id: str) -> bool:
        return self.exists

    async def count_fighter_odds(self, fighter_id: str, *, min_quality: str | None = None) -> int:
        return self.total

    async def list_fighter_odds(
        self,
        fighter_id: str,
        *,
        limit: int | None = None,
        min_quality: str | None = None,
    ) -> list[SimpleNamespace]:
        return list(self.rows)

    async def get_odds_by_id(self, odds_id: str) -> SimpleNamespace | None:
        return self.detail_row if self.detail_row and self.detail_row.id == odds_id else None

    async def get_quality_stats(self) -> dict:
        return self.stats_payload


def _row(**overrides):
    base = {
        "id": "odds-1",
        "fighter_id": "fighter-1",
        "opponent_name": "Opponent",
        "event_name": "Event",
        "event_date": None,
        "event_url": "https://example.com/event",
        "opening_odds": "+110",
        "closing_range_start": "+120",
        "closing_range_end": "+130",
        "mean_odds_history": [
            {"timestamp_ms": 2, "timestamp": "2024-01-01T00:00:02Z", "odds": 2.1},
            {"timestamp_ms": 1, "timestamp": "2024-01-01T00:00:01Z", "odds": 2.0},
        ],
        "num_odds_points": 2,
        "data_quality_tier": "good",
        "scraped_at": datetime(2024, 1, 1, 12, 0, 0),
        "bfo_fighter_url": "https://example.com/fighter",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_history_returns_none_for_missing_fighter() -> None:
    repo = StubRepository()
    repo.exists = False
    service = OddsQueryService(repo, cache=None)

    result = await service.get_fighter_odds_history("missing")
    assert result is None


@pytest.mark.asyncio
async def test_history_includes_summary_counts() -> None:
    repo = StubRepository()
    repo.total = 1
    repo.rows = [_row()]
    service = OddsQueryService(repo, cache=None)

    response = await service.get_fighter_odds_history("fighter-1")
    assert isinstance(response, FighterOddsHistoryResponse)
    assert response.total_fights == 1
    assert response.returned == 1
    assert response.odds_history[0].data_quality == "good"


@pytest.mark.asyncio
async def test_invalid_quality_raises() -> None:
    repo = StubRepository()
    service = OddsQueryService(repo, cache=None)

    with pytest.raises(InvalidQualityTierError):
        await service.get_fighter_odds_history("fighter-1", min_quality="legendary")


@pytest.mark.asyncio
async def test_chart_sorts_time_series() -> None:
    repo = StubRepository()
    repo.rows = [_row(id="chart-1")]
    service = OddsQueryService(repo, cache=None)

    response = await service.get_fighter_odds_chart("fighter-1")
    assert response is not None
    series = response.fights[0].time_series
    assert [point.timestamp_ms for point in series] == [1, 2]


@pytest.mark.asyncio
async def test_detail_payload_includes_history() -> None:
    repo = StubRepository()
    repo.detail_row = _row()
    service = OddsQueryService(repo, cache=None)

    detail = await service.get_fight_odds_detail("odds-1")
    assert detail is not None
    assert detail.closing_range is not None
    assert len(detail.mean_odds_history) == 2


@pytest.mark.asyncio
async def test_stats_adapts_repository_payload() -> None:
    repo = StubRepository()
    repo.stats_payload = {
        "total_records": 5,
        "unique_fighters": 2,
        "avg_odds_points": 42.0,
        "quality_distribution": {"excellent": 3, "good": 2, "usable": 0, "poor": 0, "no_data": 0},
        "coverage": {"fighters_with_odds": 2, "total_fighters": 3, "coverage_percentage": 66.6},
    }
    service = OddsQueryService(repo, cache=None)

    stats = await service.get_quality_stats()
    assert isinstance(stats, OddsQualityStatsResponse)
    assert stats.total_records == 5
    assert stats.coverage_stats.coverage_percentage == 66.6
