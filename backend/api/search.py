from fastapi import APIRouter, Depends, Query

from backend.schemas.fighter import FighterListItem
from backend.services.search_service import SearchService, get_search_service

router = APIRouter()


@router.get("/", response_model=list[FighterListItem])
async def search_fighters(
    q: str = Query(..., min_length=1),
    stance: str | None = Query(None),
    service: SearchService = Depends(get_search_service),
) -> list[FighterListItem]:
    return await service.search_fighters(query=q, stance=stance)
