"""Service layer for fighter rankings business logic."""

from __future__ import annotations

import logging
from datetime import date

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import get_db
from backend.db.repositories.ranking_repository import RankingRepository
from backend.schemas.ranking import (
    AllRankingsResponse,
    CurrentRankingsResponse,
    DivisionListResponse,
    PeakRankingResponse,
    RankingEntry,
    RankingHistoryEntry,
    RankingHistoryResponse,
)

logger = logging.getLogger(__name__)


class RankingService:
    """Service for managing fighter rankings operations."""

    def __init__(self, session: AsyncSession):
        """Initialize ranking service with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session
        self.repository = RankingRepository(session)

    async def get_current_rankings(
        self, division: str, source: str = "ufc"
    ) -> CurrentRankingsResponse:
        """Get current rankings for a specific division.

        Args:
            division: Weight class (e.g., 'Lightweight')
            source: Ranking source ('ufc', 'fightmatrix', 'tapology')

        Returns:
            CurrentRankingsResponse with ranked fighters
        """
        rankings_data = await self.repository.get_current_rankings(division, source)

        if not rankings_data:
            # Return empty response if no rankings found
            latest_date = await self.repository.get_latest_ranking_date(source)
            return CurrentRankingsResponse(
                division=division,
                source=source,
                rank_date=latest_date or date.today(),
                rankings=[],
                total_fighters=0,
            )

        # Convert repository data to response schema
        rankings = [
            RankingEntry(
                ranking_id=r["ranking_id"],
                fighter_id=r["fighter_id"],
                fighter_name=r["fighter_name"],
                nickname=r.get("nickname"),
                rank=r["rank"],
                previous_rank=r.get("previous_rank"),
                rank_movement=r.get("rank_movement", 0),
                is_interim=r.get("is_interim", False),
            )
            for r in rankings_data
        ]

        return CurrentRankingsResponse(
            division=division,
            source=source,
            rank_date=rankings_data[0]["rank_date"],
            rankings=rankings,
            total_fighters=len(rankings),
        )

    async def get_fighter_ranking_history(
        self,
        fighter_id: str,
        fighter_name: str,
        source: str = "ufc",
        limit: int | None = None,
    ) -> RankingHistoryResponse:
        """Get historical rankings for a specific fighter.

        Args:
            fighter_id: Fighter's UUID
            fighter_name: Fighter's full name (for response)
            source: Ranking source
            limit: Optional limit on number of records

        Returns:
            RankingHistoryResponse with timeline
        """
        history_data = await self.repository.get_fighter_ranking_history(
            fighter_id, source, limit
        )

        history = [
            RankingHistoryEntry(
                ranking_id=h["ranking_id"],
                division=h["division"],
                rank=h["rank"],
                previous_rank=h.get("previous_rank"),
                rank_movement=h.get("rank_movement", 0),
                is_interim=h.get("is_interim", False),
                rank_date=h["rank_date"],
                source=h["source"],
            )
            for h in history_data
        ]

        return RankingHistoryResponse(
            fighter_id=fighter_id,
            fighter_name=fighter_name,
            source=source,
            history=history,
            total_snapshots=len(history),
        )

    async def get_peak_ranking(
        self, fighter_id: str, fighter_name: str, source: str = "ufc"
    ) -> PeakRankingResponse | None:
        """Get fighter's best ranking achievement.

        Args:
            fighter_id: Fighter's UUID
            fighter_name: Fighter's full name
            source: Ranking source

        Returns:
            PeakRankingResponse or None if never ranked
        """
        peak_data = await self.repository.get_peak_ranking(fighter_id, source)

        if not peak_data:
            return None

        return PeakRankingResponse(
            fighter_id=fighter_id,
            fighter_name=fighter_name,
            division=peak_data["division"],
            peak_rank=peak_data["peak_rank"],
            rank_date=peak_data["rank_date"],
            is_interim=peak_data.get("is_interim", False),
            source=peak_data["source"],
        )

    async def get_all_divisions(self, source: str = "ufc") -> DivisionListResponse:
        """Get list of all divisions with rankings.

        Args:
            source: Ranking source

        Returns:
            DivisionListResponse with available divisions
        """
        divisions = await self.repository.get_all_divisions(source)

        return DivisionListResponse(
            divisions=divisions, source=source, total_divisions=len(divisions)
        )

    async def get_all_rankings(self, source: str = "ufc") -> AllRankingsResponse:
        """Get current rankings for all divisions.

        Args:
            source: Ranking source

        Returns:
            AllRankingsResponse with all division rankings
        """
        # Get all divisions
        divisions = await self.repository.get_all_divisions(source)

        # Get latest ranking date
        latest_date = await self.repository.get_latest_ranking_date(source)

        if not latest_date:
            return AllRankingsResponse(
                source=source,
                rank_date=date.today(),
                divisions=[],
                total_divisions=0,
                total_fighters=0,
            )

        # Fetch rankings for each division
        division_rankings = []
        total_fighters = 0

        for division in divisions:
            division_response = await self.get_current_rankings(division, source)
            division_rankings.append(division_response)
            total_fighters += division_response.total_fighters

        return AllRankingsResponse(
            source=source,
            rank_date=latest_date,
            divisions=division_rankings,
            total_divisions=len(divisions),
            total_fighters=total_fighters,
        )


def get_ranking_service(session: AsyncSession = Depends(get_db)) -> RankingService:
    """Dependency injection for RankingService.

    Args:
        session: Async database session from FastAPI dependency

    Returns:
        RankingService instance
    """
    return RankingService(session)
