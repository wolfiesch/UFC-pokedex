from fastapi import APIRouter, Depends, HTTPException, Query

from backend.schemas.fighter import (
    FighterComparisonResponse,
    FighterDetail,
    FighterListItem,
    PaginatedFightersResponse,
)
from backend.services.fighter_query_service import (
    FighterQueryService,
    get_fighter_query_service,
)

router = APIRouter()


@router.get("/", response_model=PaginatedFightersResponse)
@router.get("", response_model=PaginatedFightersResponse, include_in_schema=False)
async def list_fighters(
    limit: int = Query(20, ge=1, le=100, description="Number of fighters to return"),
    offset: int = Query(0, ge=0, description="Number of fighters to skip"),
    include_streak: bool = Query(
        False,
        description=(
            "When true, include lightweight current streak fields in list payloads."
        ),
    ),
    streak_window: int = Query(
        6,
        ge=2,
        le=20,
        description="How many recent fights to examine when computing a current streak.",
    ),
    service: FighterQueryService = Depends(get_fighter_query_service),
) -> PaginatedFightersResponse:
    """List fighters with pagination."""
    fighters = await service.list_fighters(
        limit=limit,
        offset=offset,
        include_streak=include_streak,
        streak_window=streak_window,
    )
    total = await service.count_fighters()
    return PaginatedFightersResponse(
        fighters=fighters,
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + limit < total,
    )


@router.get("/random", response_model=FighterListItem)
async def get_random_fighter(
    service: FighterQueryService = Depends(get_fighter_query_service),
) -> FighterListItem:
    """Get a random fighter from the database."""
    fighter = await service.get_random_fighter()
    if not fighter:
        raise HTTPException(status_code=404, detail="No fighters found")
    return fighter


@router.get("/compare", response_model=FighterComparisonResponse)
async def compare_fighters(
    fighter_ids: list[str] = Query(
        ..., description="Repeated or comma-separated fighter IDs to compare"
    ),
    service: FighterQueryService = Depends(get_fighter_query_service),
) -> FighterComparisonResponse:
    """Return side-by-side stat snapshots for the requested fighters."""

    parsed_ids: list[str] = []
    for token in fighter_ids:
        parts = [part.strip() for part in token.split(",") if part and part.strip()]
        for part in parts:
            if part not in parsed_ids:
                parsed_ids.append(part)

    if len(parsed_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="Provide at least two fighter_ids to calculate a comparison.",
        )

    fighters = await service.compare_fighters(parsed_ids)
    if not fighters:
        raise HTTPException(status_code=404, detail="Unable to locate fighters")

    return FighterComparisonResponse(fighters=fighters)


@router.get("/{fighter_id}", response_model=FighterDetail)
async def get_fighter(
    fighter_id: str,
    service: FighterQueryService = Depends(get_fighter_query_service),
) -> FighterDetail:
    fighter = await service.get_fighter(fighter_id)
    if not fighter:
        raise HTTPException(status_code=404, detail="Fighter not found")
    return fighter
