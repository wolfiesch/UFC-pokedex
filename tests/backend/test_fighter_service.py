from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

pytest.importorskip("pytest_asyncio")
pytest.importorskip("sqlalchemy")

pytest_asyncio = pytest.importorskip("pytest_asyncio")

from backend.schemas.fighter import FighterComparisonEntry
from backend.services.fighter_service import FighterService


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
