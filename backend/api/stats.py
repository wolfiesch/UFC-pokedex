from fastapi import APIRouter, Depends

from backend.services.fighter_service import FighterService, get_fighter_service

router = APIRouter()


@router.get("/summary")
async def stats_summary(
    service: FighterService = Depends(get_fighter_service),
) -> dict[str, float]:
    return await service.get_stats_summary()
