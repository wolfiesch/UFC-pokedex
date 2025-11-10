"""API endpoints for fighter rankings."""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.db.repositories.fighter_repository import FighterRepository
from backend.db.connection import get_db
from backend.schemas.ranking import (
    AllRankingsResponse,
    CurrentRankingsResponse,
    DivisionListResponse,
    PeakRankingResponse,
    RankingHistoryResponse,
)
from backend.services.ranking_service import RankingService, get_ranking_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/", response_model=AllRankingsResponse)
@router.get("", response_model=AllRankingsResponse, include_in_schema=False)
async def get_all_rankings(
    source: str = Query(
        "ufc",
        description="Ranking source: 'ufc', 'fightmatrix', or 'tapology'",
        regex="^(ufc|fightmatrix|tapology)$",
    ),
    service: RankingService = Depends(get_ranking_service),
) -> AllRankingsResponse:
    """Get current rankings for all divisions.

    Returns the most recent rankings snapshot across all weight classes
    from the specified source.

    Args:
        source: Ranking source (ufc, fightmatrix, tapology)
        service: Ranking service dependency

    Returns:
        All rankings organized by division
    """
    return await service.get_all_rankings(source)


@router.get("/divisions", response_model=DivisionListResponse)
async def get_divisions(
    source: str = Query(
        "ufc",
        description="Ranking source",
        regex="^(ufc|fightmatrix|tapology)$",
    ),
    service: RankingService = Depends(get_ranking_service),
) -> DivisionListResponse:
    """Get list of all divisions with rankings available.

    Args:
        source: Ranking source
        service: Ranking service dependency

    Returns:
        List of division names
    """
    return await service.get_all_divisions(source)


@router.get("/{division}", response_model=CurrentRankingsResponse)
async def get_division_rankings(
    division: str,
    source: str = Query(
        "ufc",
        description="Ranking source",
        regex="^(ufc|fightmatrix|tapology)$",
    ),
    service: RankingService = Depends(get_ranking_service),
) -> CurrentRankingsResponse:
    """Get current rankings for a specific division.

    Returns the most recent ranking snapshot for the specified weight class.

    Args:
        division: Weight class (e.g., 'Lightweight', 'Heavyweight')
        source: Ranking source
        service: Ranking service dependency

    Returns:
        Division rankings with fighter details
    """
    response = await service.get_current_rankings(division, source)

    if not response.rankings:
        raise HTTPException(
            status_code=404,
            detail=f"No rankings found for division '{division}' from source '{source}'",
        )

    return response


@router.get("/fighter/{fighter_id}/history", response_model=RankingHistoryResponse)
async def get_fighter_ranking_history(
    fighter_id: str,
    source: str = Query(
        "ufc",
        description="Ranking source",
        regex="^(ufc|fightmatrix|tapology)$",
    ),
    limit: int = Query(
        None,
        ge=1,
        le=100,
        description="Optional limit on number of historical snapshots",
    ),
    service: RankingService = Depends(get_ranking_service),
    session: AsyncSession = Depends(get_db),
) -> RankingHistoryResponse:
    """Get historical ranking progression for a fighter.

    Returns a timeline of the fighter's ranking snapshots ordered by date
    (most recent first).

    Args:
        fighter_id: Fighter's UUID
        source: Ranking source
        limit: Optional limit on number of records
        service: Ranking service dependency
        session: Database session

    Returns:
        Fighter's ranking history
    """
    # Fetch fighter name from database
    fighter_repo = FighterRepository(session)
    fighter = await fighter_repo.get_fighter(fighter_id)

    if not fighter:
        raise HTTPException(status_code=404, detail="Fighter not found")

    response = await service.get_fighter_ranking_history(
        fighter_id, fighter.name, source, limit
    )

    if not response.history:
        raise HTTPException(
            status_code=404,
            detail=f"No ranking history found for fighter '{fighter.name}' from source '{source}'",
        )

    return response


@router.get("/fighter/{fighter_id}/peak", response_model=PeakRankingResponse)
async def get_fighter_peak_ranking(
    fighter_id: str,
    source: str = Query(
        "ufc",
        description="Ranking source",
        regex="^(ufc|fightmatrix|tapology)$",
    ),
    service: RankingService = Depends(get_ranking_service),
    session: AsyncSession = Depends(get_db),
) -> PeakRankingResponse:
    """Get fighter's best ranking achievement.

    Returns the fighter's highest (lowest number) ranking ever achieved
    from the specified source.

    Args:
        fighter_id: Fighter's UUID
        source: Ranking source
        service: Ranking service dependency
        session: Database session

    Returns:
        Fighter's peak ranking
    """
    # Fetch fighter name from database
    fighter_repo = FighterRepository(session)
    fighter = await fighter_repo.get_fighter(fighter_id)

    if not fighter:
        raise HTTPException(status_code=404, detail="Fighter not found")

    peak = await service.get_peak_ranking(fighter_id, fighter.name, source)

    if not peak:
        raise HTTPException(
            status_code=404,
            detail=f"No ranking history found for fighter '{fighter.name}' from source '{source}'",
        )

    return peak
