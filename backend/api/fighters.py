from fastapi import APIRouter, Depends, HTTPException

from backend.schemas.fighter import FighterDetail, FighterListItem
from backend.services.fighter_service import FighterService, get_fighter_service

router = APIRouter()


@router.get("/", response_model=list[FighterListItem])
async def list_fighters(
    service: FighterService = Depends(get_fighter_service),
) -> list[FighterListItem]:
    return await service.list_fighters()


@router.get("/{fighter_id}", response_model=FighterDetail)
async def get_fighter(
    fighter_id: str,
    service: FighterService = Depends(get_fighter_service),
) -> FighterDetail:
    fighter = await service.get_fighter(fighter_id)
    if not fighter:
        raise HTTPException(status_code=404, detail="Fighter not found")
    return fighter
