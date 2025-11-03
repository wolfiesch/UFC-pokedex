from fastapi import APIRouter, Depends, Query

from backend.schemas.fighter import PaginatedFightersResponse
from backend.services.search_service import SearchService, get_search_service

router = APIRouter()


@router.get("/", response_model=PaginatedFightersResponse)
async def search_fighters(
    q: str = Query("", description="Fighter name or nickname query."),
    stance: str | None = Query(None, description="Optional stance filter."),
    division: str | None = Query(None, description="Optional division filter."),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return."),
    offset: int = Query(0, ge=0, description="Number of matches to skip."),
    service: SearchService = Depends(get_search_service),
) -> PaginatedFightersResponse:
    return await service.search_fighters(
        query=q or None,
        stance=stance,
        division=division,
        limit=limit,
        offset=offset,
    )
