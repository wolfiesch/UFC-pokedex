from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, Literal

import pytest

from backend.schemas.fighter import (
    FighterComparisonEntry,
    FighterDetail,
    FighterListItem,
)
from backend.services.fighter_query_service import (
    FighterQueryService,
    FighterRepositoryProtocol,
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

    async def search_fighters(
        self,
        query: str | None = None,
        stance: str | None = None,
        division: str | None = None,
        champion_statuses: list[str] | None = None,
        streak_type: Literal["win", "loss"] | None = None,
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


@pytest.mark.asyncio
async def test_compare_fighters_preserves_requested_order() -> None:
    repository = FakeComparisonRepository()
    cache = FakeCache()
    service = FighterQueryService(repository, cache=cache)

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
        async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
            return None

    assert not isinstance(IncompleteRepository(), FighterRepositoryProtocol)
