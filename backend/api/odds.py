"""FastAPI router exposing betting odds endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.schemas.odds import (
    FighterOddsChartResponse,
    FighterOddsHistoryResponse,
    FightOddsDetailResponse,
    OddsQualityStatsResponse,
)
from backend.services.dependencies import get_odds_query_service
from backend.services.odds_query_service import (
    InvalidQualityTierError,
    OddsQueryService,
)

router = APIRouter()


@router.get(
    "/fighter/{fighter_id}",
    response_model=FighterOddsHistoryResponse,
    summary="List betting odds for a fighter",
)
async def get_fighter_odds_history(
    fighter_id: str,
    limit: int = Query(
        100,
        ge=1,
        le=500,
        description="Maximum number of fights to return (max 500).",
    ),
    quality_min: str | None = Query(
        None,
        description="Minimum quality tier (excellent, good, usable, poor, no_data).",
    ),
    service: OddsQueryService = Depends(get_odds_query_service),
) -> FighterOddsHistoryResponse:
    try:
        response = await service.get_fighter_odds_history(
            fighter_id, limit=limit, min_quality=quality_min
        )
    except InvalidQualityTierError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if response is None:
        raise HTTPException(status_code=404, detail="Fighter not found")
    return response


@router.get(
    "/fighter/{fighter_id}/chart",
    response_model=FighterOddsChartResponse,
    summary="Return chart-ready odds data for a fighter",
)
async def get_fighter_odds_chart(
    fighter_id: str,
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of fights to include in the chart payload.",
    ),
    service: OddsQueryService = Depends(get_odds_query_service),
) -> FighterOddsChartResponse:
    response = await service.get_fighter_odds_chart(fighter_id, limit=limit)
    if response is None:
        raise HTTPException(status_code=404, detail="Fighter not found")
    return response


@router.get(
    "/fight/{odds_id}",
    response_model=FightOddsDetailResponse,
    summary="Retrieve the full odds record for a single fight",
)
async def get_fight_odds_detail(
    odds_id: str,
    service: OddsQueryService = Depends(get_odds_query_service),
) -> FightOddsDetailResponse:
    response = await service.get_fight_odds_detail(odds_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Odds record not found")
    return response


@router.get(
    "/stats/quality",
    response_model=OddsQualityStatsResponse,
    summary="Dataset quality metrics",
)
async def get_odds_quality_stats(
    service: OddsQueryService = Depends(get_odds_query_service),
) -> OddsQualityStatsResponse:
    return await service.get_quality_stats()


__all__ = ["router"]
