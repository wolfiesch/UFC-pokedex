from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.schemas.fighter import PaginatedFightersResponse
from backend.services.search_service import SearchService, get_search_service

router = APIRouter()


@router.get("/", response_model=PaginatedFightersResponse)
async def search_fighters(
    q: str = Query("", description="Fighter name, nickname, or location query."),
    stance: str | None = Query(None, description="Optional stance filter."),
    division: str | None = Query(None, description="Optional division filter."),
    champion_statuses: list[str] | None = Query(
        None,
        description=(
            "Filter by champion status. Options: 'current', 'former'. "
            "Multiple values allowed (OR logic)."
        ),
    ),
    streak_type: Literal["win", "loss"] | None = Query(
        None, description="Filter by streak type. Options: 'win', 'loss'."
    ),
    min_streak_count: int | None = Query(
        None,
        ge=1,
        le=20,
        description="Minimum streak count (only used when streak_type is specified).",
    ),
    include_locations: bool = Query(
        True,
        description="Include location fields in search (birthplace, nationality, training gym).",
    ),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return."),
    offset: int = Query(0, ge=0, description="Number of matches to skip."),
    service: SearchService = Depends(get_search_service),
) -> PaginatedFightersResponse:
    """Search fighters by name, nickname, or location.

    Examples:
        /search/?q=dublin      # Finds fighters from Dublin
        /search/?q=aka         # Finds fighters from AKA gym
        /search/?q=brazilian   # Finds Brazilian fighters
    """

    # Validate streak parameters are used together
    if (streak_type is None) != (min_streak_count is None):
        raise HTTPException(
            status_code=422, detail="streak_type and min_streak_count must be provided together"
        )

    return await service.search_fighters(
        query=q or None,
        stance=stance,
        division=division,
        champion_statuses=champion_statuses,
        streak_type=streak_type,
        min_streak_count=min_streak_count,
        include_locations=include_locations,
        limit=limit,
        offset=offset,
    )
