from __future__ import annotations

from typing import cast

import pytest

from backend.cache import (
    CacheClient,
    invalidate_fighter,
    local_cache_clear_all,
)
from backend.schemas.fighter import FighterDetail, FighterListItem
from backend.services.fighter_service import FighterRepositoryProtocol, FighterService


class MutableFighterRepository:
    """Mutable repository that mimics database-backed fighter persistence."""

    def __init__(self) -> None:
        self._fighters: dict[str, FighterDetail] = {
            "alpha": FighterDetail(
                fighter_id="alpha",
                detail_url="https://example.test/fighters/alpha",
                name="Original Alpha",
                nickname="The Pioneer",
                record="1-0-0",
                division="Lightweight",
            )
        }

    async def list_fighters(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        include_streak: bool = False,
        streak_window: int = 6,
    ) -> list[FighterListItem]:
        """Return fighter list items derived from the mutable detail store."""

        # The real repository performs pagination, but for regression safety we keep the
        # data shape faithful and simply return all values.
        return [
            FighterListItem.model_validate(fighter.model_dump())
            for fighter in self._fighters.values()
        ]

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Return a deep copy of the fighter detail to simulate ORM behavior."""

        fighter = self._fighters.get(fighter_id)
        if fighter is None:
            return None
        return FighterDetail.model_validate(fighter.model_dump())

    def update_fighter_name(self, fighter_id: str, name: str) -> None:
        """Mutate the stored fighter detail to emulate an upstream data change."""

        if fighter_id not in self._fighters:
            msg = f"Unknown fighter id: {fighter_id}"
            raise KeyError(msg)
        self._fighters[fighter_id] = self._fighters[fighter_id].model_copy(update={"name": name})


@pytest.mark.asyncio
async def test_invalidate_fighter_clears_local_cache() -> None:
    """Local fallback caches must reflect mutations once invalidation runs."""

    await local_cache_clear_all()
    repository = MutableFighterRepository()
    service = FighterService(cast(FighterRepositoryProtocol, repository), cache=None)

    first_detail = await service.get_fighter("alpha")
    assert first_detail is not None
    assert first_detail.name == "Original Alpha"

    first_list = await service.list_fighters(limit=10, offset=0)
    assert [item.name for item in first_list] == ["Original Alpha"]

    repository.update_fighter_name("alpha", "Updated Alpha")

    # Cached responses should still surface stale data prior to invalidation.
    cached_detail = await service.get_fighter("alpha")
    assert cached_detail is not None
    assert cached_detail.name == "Original Alpha"

    cached_list = await service.list_fighters(limit=10, offset=0)
    assert [item.name for item in cached_list] == ["Original Alpha"]

    # Trigger invalidation using a CacheClient without Redis backing.
    cache_client = CacheClient(redis=None)
    await invalidate_fighter(cache_client, "alpha")

    refreshed_detail = await service.get_fighter("alpha")
    assert refreshed_detail is not None
    assert refreshed_detail.name == "Updated Alpha"

    refreshed_list = await service.list_fighters(limit=10, offset=0)
    assert [item.name for item in refreshed_list] == ["Updated Alpha"]
