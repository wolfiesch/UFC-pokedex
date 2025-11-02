from __future__ import annotations

from fastapi import Depends

from backend.schemas.fighter import PaginatedFightersResponse
from backend.services.fighter_service import FighterService, get_fighter_service


class SearchService:
    def __init__(self, fighter_service: FighterService) -> None:
        self._fighter_service = fighter_service

    async def search_fighters(
        self,
        query: str | None = None,
        stance: str | None = None,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> PaginatedFightersResponse:
        """Search fighters using the fighter service's search method."""

        return await self._fighter_service.search_fighters(
            query=query,
            stance=stance,
            limit=limit,
            offset=offset,
        )


def get_search_service(
    fighter_service: FighterService = Depends(get_fighter_service),
) -> SearchService:
    return SearchService(fighter_service)
