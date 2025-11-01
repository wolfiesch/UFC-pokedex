from fastapi import APIRouter, Depends, HTTPException, Query

from backend.schemas.fighter import FighterDetail, FighterListItem, PaginatedFightersResponse
from backend.services.fighter_service import FighterService, get_fighter_service

router = APIRouter()


@router.get("/", response_model=PaginatedFightersResponse)
async def list_fighters(
    limit: int = Query(20, ge=1, le=100, description="Number of fighters to return"),
    offset: int = Query(0, ge=0, description="Number of fighters to skip"),
    service: FighterService = Depends(get_fighter_service),
) -> PaginatedFightersResponse:
    """List fighters with pagination."""
    fighters = await service.list_fighters(limit=limit, offset=offset)
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
    service: FighterService = Depends(get_fighter_service),
) -> FighterListItem:
    """Get a random fighter from the database."""
    fighter = await service.get_random_fighter()
    if not fighter:
        raise HTTPException(status_code=404, detail="No fighters found")
    return fighter


@router.get("/{fighter_id}", response_model=FighterDetail)
async def get_fighter(
    fighter_id: str,
    service: FighterService = Depends(get_fighter_service),
) -> FighterDetail:
    fighter = await service.get_fighter(fighter_id)
    if not fighter:
        raise HTTPException(status_code=404, detail="Fighter not found")
    return fighter
