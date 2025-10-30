from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from backend.schemas.fighter import FighterDetail, FighterListItem


class FighterRepositoryProtocol:
    async def list_fighters(self) -> Iterable[FighterListItem]:
        raise NotImplementedError

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        raise NotImplementedError

    async def stats_summary(self) -> dict[str, float]:
        raise NotImplementedError


class InMemoryFighterRepository(FighterRepositoryProtocol):
    """Temporary repository used until database layer is implemented."""

    def __init__(self) -> None:
        self._fighters = {
            "sample-fighter": FighterDetail(
                fighter_id="sample-fighter",
                name="Sample Fighter",
                nickname="Prototype",
                height="6'0\"",
                weight="170 lbs.",
                reach="74\"",
                stance="Orthodox",
                dob=date(1990, 1, 1),
                record="10-2-0",
                striking={"sig_strikes_landed_per_min": 3.5},
                grappling={"takedown_accuracy": "45%"},
                fight_history=[],
            )
        }

    async def list_fighters(self) -> Iterable[FighterListItem]:
        return list(self._fighters.values())

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        return self._fighters.get(fighter_id)

    async def stats_summary(self) -> dict[str, float]:
        return {"fighters_indexed": float(len(self._fighters))}


class FighterService:
    def __init__(self, repository: FighterRepositoryProtocol | None = None) -> None:
        self._repository = repository or InMemoryFighterRepository()

    async def list_fighters(self) -> list[FighterListItem]:
        fighters = await self._repository.list_fighters()
        return list(fighters)

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        return await self._repository.get_fighter(fighter_id)

    async def get_stats_summary(self) -> dict[str, float]:
        return await self._repository.stats_summary()


def get_fighter_service() -> FighterService:
    return FighterService()
