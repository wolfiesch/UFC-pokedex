from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from typing import Any, Literal

import pytest

from backend.schemas.fight_graph import FightGraphResponse
from backend.schemas.fighter import (
    FighterComparisonEntry,
    FighterDetail,
    FighterListItem,
)
from backend.schemas.stats import (
    LeaderboardMetricId,
    LeaderboardsResponse,
    StatsSummaryResponse,
    TrendTimeBucket,
    TrendsResponse,
)
from backend.services.fighter_service import (
    FighterRepositoryProtocol,
    FighterService,
    InMemoryFighterRepository,
)

pytest.importorskip("pytest_asyncio")
pytest.importorskip("sqlalchemy")


class FakeCache:
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    async def get_json(self, key: str) -> Any:
        return self._store.get(key)

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        self._store[key] = value


class FakeComparisonRepository:
    def __init__(self) -> None:
        self.calls: list[Sequence[str]] = []

    async def get_fighters_for_comparison(
        self, fighter_ids: Sequence[str]
    ) -> list[FighterComparisonEntry]:
        self.calls.append(tuple(fighter_ids))
        entries: list[FighterComparisonEntry] = []
        for fighter_id in fighter_ids:
            entries.append(
                FighterComparisonEntry(
                    fighter_id=fighter_id,
                    name=f"Fighter {fighter_id.upper()}",
                )
            )
        return entries

    # -- Protocol compliance stubs -------------------------------------------------

    async def list_fighters(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        include_streak: bool = False,
        streak_window: int = 6,
    ) -> Iterable[FighterListItem]:
        """Not used in this test double."""

        raise NotImplementedError

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Not used in this test double."""

        raise NotImplementedError

    async def stats_summary(self) -> StatsSummaryResponse:
        """Not used in this test double."""

        raise NotImplementedError

    async def get_leaderboards(
        self,
        *,
        limit: int,
        accuracy_metric: LeaderboardMetricId,
        submissions_metric: LeaderboardMetricId,
        start_date: date | None,
        end_date: date | None,
    ) -> LeaderboardsResponse:
        """Not used in this test double."""

        raise NotImplementedError

    async def get_trends(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        time_bucket: TrendTimeBucket,
        streak_limit: int,
    ) -> TrendsResponse:
        """Not used in this test double."""

        raise NotImplementedError

    async def search_fighters(
        self,
        query: str | None = None,
        stance: str | None = None,
        division: str | None = None,
        champion_statuses: list[str] | None = None,
        streak_type: Literal["win", "loss", "draw", "none"] | None = None,
        min_streak_count: int | None = None,
        include_streak: bool = False,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[list[FighterListItem], int]:
        """Not used in this test double."""

        raise NotImplementedError

    async def count_fighters(self) -> int:
        """Not used in this test double."""

        raise NotImplementedError

    async def get_random_fighter(self) -> FighterListItem | None:
        """Not used in this test double."""

        raise NotImplementedError

    async def get_fight_graph(
        self,
        *,
        division: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 200,
        include_upcoming: bool = False,
    ) -> FightGraphResponse:
        """Not used in this test double."""

        raise NotImplementedError


@pytest.mark.asyncio
async def test_compare_fighters_preserves_requested_order() -> None:
    repository = FakeComparisonRepository()
    cache = FakeCache()
    service = FighterService(repository, cache=cache)

    first = await service.compare_fighters(["alpha", "beta"])
    assert [entry.fighter_id for entry in first] == ["alpha", "beta"]
    assert repository.calls == [("alpha", "beta")]

    # Second call with the same ordering should be served from cache.
    second = await service.compare_fighters(["alpha", "beta"])
    assert [entry.fighter_id for entry in second] == ["alpha", "beta"]
    assert repository.calls == [("alpha", "beta")]

    # Different ordering should trigger a fresh repository call but keep order.
    third = await service.compare_fighters(["beta", "alpha"])
    assert [entry.fighter_id for entry in third] == ["beta", "alpha"]
    assert repository.calls == [("alpha", "beta"), ("beta", "alpha")]


def test_in_memory_repository_conforms_to_protocol() -> None:
    """Ensure the built-in in-memory repository satisfies the protocol."""

    repository = InMemoryFighterRepository()
    assert isinstance(repository, FighterRepositoryProtocol)


def test_protocol_runtime_check_detects_missing_methods() -> None:
    """Objects missing protocol methods should fail runtime conformance checks."""

    class IncompleteRepository:
        async def list_fighters(
            self, *, limit: int | None = None
        ) -> Iterable[FighterListItem]:
            return []

    assert not isinstance(IncompleteRepository(), FighterRepositoryProtocol)
