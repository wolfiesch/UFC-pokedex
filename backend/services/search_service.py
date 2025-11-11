from __future__ import annotations

from typing import Literal

from fastapi import Depends

from backend.schemas.fighter import PaginatedFightersResponse
from backend.services.fighter_query_service import (
    FighterQueryService,
    get_fighter_query_service,
)


class SearchService:
    def __init__(self, fighter_service: FighterQueryService) -> None:
        self._fighter_service = fighter_service

    async def search_fighters(
        self,
        query: str | None = None,
        stance: str | None = None,
        division: str | None = None,
        champion_statuses: list[str] | None = None,
        streak_type: Literal["win", "loss"] | None = None,
        min_streak_count: int | None = None,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> PaginatedFightersResponse:
        """Search fighters using the fighter service's search method."""

        # Determine if we need to include streak data
        include_streak = streak_type is not None and min_streak_count is not None

        return await self._fighter_service.search_fighters(
            query=query,
            stance=stance,
            division=division,
            champion_statuses=champion_statuses,
            streak_type=streak_type,
            min_streak_count=min_streak_count,
            include_streak=include_streak,
            limit=limit,
            offset=offset,
        )


def get_search_service(
    fighter_service: FighterQueryService = Depends(get_fighter_query_service),
) -> SearchService:
    return SearchService(fighter_service)
