from fastapi import APIRouter, Depends, HTTPException, Query

from backend.schemas.fight_graph import FightGraphResponse
from backend.services.fighter_service import FighterService, get_fighter_service

router = APIRouter()


@router.get("/graph", response_model=FightGraphResponse)
async def get_fight_graph(
    division: str | None = Query(
        default=None,
        description="Optional weight class / division filter (e.g., 'Lightweight').",
    ),
    start_year: int | None = Query(
        default=None,
        ge=1900,
        le=2100,
        description="Earliest fight year to include.",
    ),
    end_year: int | None = Query(
        default=None,
        ge=1900,
        le=2100,
        description="Latest fight year to include.",
    ),
    limit: int = Query(
        default=200,
        ge=1,
        le=500,
        description="Maximum number of fighters to include in the graph payload.",
    ),
    include_upcoming: bool = Query(
        default=False,
        description="Include bouts marked as upcoming (result='Next').",
    ),
    service: FighterService = Depends(get_fighter_service),
) -> FightGraphResponse:
    """Return a graph-friendly representation of fighters and their shared bouts."""

    # Validated metadata now includes pre-computed insights for UI panels, so
    # keep inputs tidy to ensure consistent caching behaviour downstream.

    if start_year is not None and end_year is not None and start_year > end_year:
        raise HTTPException(
            status_code=400,
            detail="start_year must be less than or equal to end_year",
        )

    return await service.get_fight_graph(
        division=division,
        start_year=start_year,
        end_year=end_year,
        limit=limit,
        include_upcoming=include_upcoming,
    )
