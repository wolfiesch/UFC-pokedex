from __future__ import annotations

from backend.schemas.fighter import FighterListItem
from backend.services.fighter_service import FighterService, get_fighter_service


class SearchService:
    def __init__(self, fighter_service: FighterService) -> None:
        self._fighter_service = fighter_service

    async def search_fighters(self, query: str, stance: str | None = None) -> list[FighterListItem]:
        fighters = await self._fighter_service.list_fighters()
        query_lower = query.lower()
        results = [
            fighter
            for fighter in fighters
            if query_lower in fighter.name.lower()
            or (fighter.nickname and query_lower in fighter.nickname.lower())
        ]
        if stance:
            stance_lower = stance.lower()
            results = [
                fighter for fighter in results if fighter.stance and fighter.stance.lower() == stance_lower
            ]
        return results


def get_search_service(
    fighter_service: FighterService | None = None,
) -> SearchService:
    service = fighter_service or get_fighter_service()
    return SearchService(service)
