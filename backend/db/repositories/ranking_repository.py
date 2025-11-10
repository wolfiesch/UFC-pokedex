"""Repository for managing fighter rankings data access.

This repository handles all database operations related to fighter rankings
from various sources (UFC.com, Fight Matrix, etc.).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.db.models import Fighter, FighterRanking


class RankingRepository:
    """Async repository for fighter rankings data access."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def get_current_rankings(
        self,
        division: str,
        source: str = "ufc",
    ) -> list[dict[str, Any]]:
        """Get current rankings for a specific division.

        Args:
            division: Weight class (e.g., 'Lightweight')
            source: Ranking source ('ufc', 'fightmatrix', 'tapology')

        Returns:
            List of ranking dicts with fighter data, ordered by rank
        """
        # Get the most recent ranking date for this division/source
        latest_date_query = (
            select(func.max(FighterRanking.rank_date))
            .where(FighterRanking.division == division)
            .where(FighterRanking.source == source)
        )
        result = await self.session.execute(latest_date_query)
        latest_date = result.scalar_one_or_none()

        if not latest_date:
            return []

        # Get rankings for that date
        query = (
            select(FighterRanking, Fighter)
            .join(Fighter, FighterRanking.fighter_id == Fighter.id)
            .where(FighterRanking.division == division)
            .where(FighterRanking.source == source)
            .where(FighterRanking.rank_date == latest_date)
            .order_by(FighterRanking.rank.asc().nullslast())
        )

        result = await self.session.execute(query)
        rows = result.all()

        return [
            {
                "ranking_id": ranking.id,
                "fighter_id": fighter.id,
                "fighter_name": fighter.name,
                "nickname": fighter.nickname,
                "rank": ranking.rank,
                "previous_rank": ranking.previous_rank,
                "rank_movement": self._calculate_rank_movement(
                    ranking.rank, ranking.previous_rank
                ),
                "is_interim": ranking.is_interim,
                "rank_date": ranking.rank_date,
                "source": ranking.source,
            }
            for ranking, fighter in rows
        ]

    async def get_fighter_ranking_history(
        self,
        fighter_id: str,
        source: str = "ufc",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get historical rankings for a specific fighter.

        Args:
            fighter_id: Fighter's UUID
            source: Ranking source
            limit: Optional limit on number of records

        Returns:
            List of historical ranking snapshots, ordered by date desc
        """
        query = (
            select(FighterRanking)
            .where(FighterRanking.fighter_id == fighter_id)
            .where(FighterRanking.source == source)
            .order_by(desc(FighterRanking.rank_date))
        )

        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        rankings = result.scalars().all()

        return [
            {
                "ranking_id": ranking.id,
                "division": ranking.division,
                "rank": ranking.rank,
                "previous_rank": ranking.previous_rank,
                "rank_movement": self._calculate_rank_movement(
                    ranking.rank, ranking.previous_rank
                ),
                "is_interim": ranking.is_interim,
                "rank_date": ranking.rank_date,
                "source": ranking.source,
            }
            for ranking in rankings
        ]

    async def get_peak_ranking(
        self,
        fighter_id: str,
        source: str = "ufc",
    ) -> dict[str, Any] | None:
        """Get the fighter's best (lowest number) ranking ever.

        Args:
            fighter_id: Fighter's UUID
            source: Ranking source

        Returns:
            Peak ranking dict or None if fighter never ranked
        """
        # Get best rank (lowest number, excluding None/NR)
        query = (
            select(FighterRanking)
            .where(FighterRanking.fighter_id == fighter_id)
            .where(FighterRanking.source == source)
            .where(FighterRanking.rank.isnot(None))  # Exclude "Not Ranked"
            .order_by(FighterRanking.rank.asc())
            .limit(1)
        )

        result = await self.session.execute(query)
        peak_ranking = result.scalar_one_or_none()

        if not peak_ranking:
            return None

        return {
            "ranking_id": peak_ranking.id,
            "division": peak_ranking.division,
            "peak_rank": peak_ranking.rank,
            "rank_date": peak_ranking.rank_date,
            "is_interim": peak_ranking.is_interim,
            "source": peak_ranking.source,
        }

    async def upsert_ranking(self, ranking_data: dict[str, Any]) -> FighterRanking:
        """Insert or update a ranking record.

        Uses fighter_id + division + rank_date + source as unique key.

        Args:
            ranking_data: Dict with keys:
                - id: UUID
                - fighter_id: Fighter UUID
                - division: Weight class
                - rank: Rank position (0=Champion, 1-15, None=NR)
                - previous_rank: Previous rank
                - rank_date: Date of ranking
                - source: Ranking source
                - is_interim: Whether interim champion

        Returns:
            Created or updated FighterRanking model
        """
        # Check if ranking already exists
        query = (
            select(FighterRanking)
            .where(FighterRanking.fighter_id == ranking_data["fighter_id"])
            .where(FighterRanking.division == ranking_data["division"])
            .where(FighterRanking.rank_date == ranking_data["rank_date"])
            .where(FighterRanking.source == ranking_data["source"])
        )

        result = await self.session.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing record
            for key, value in ranking_data.items():
                if key != "id":  # Don't update ID
                    setattr(existing, key, value)
            await self.session.flush()
            return existing
        else:
            # Create new record
            ranking = FighterRanking(**ranking_data)
            self.session.add(ranking)
            await self.session.flush()
            return ranking

    async def bulk_upsert_rankings(
        self, rankings_data: list[dict[str, Any]]
    ) -> int:
        """Bulk insert/update multiple rankings efficiently.

        Args:
            rankings_data: List of ranking dicts (same format as upsert_ranking)

        Returns:
            Number of rankings processed
        """
        count = 0
        for ranking_data in rankings_data:
            await self.upsert_ranking(ranking_data)
            count += 1

        await self.session.flush()
        return count

    async def get_all_divisions(self, source: str = "ufc") -> list[str]:
        """Get list of all divisions with rankings.

        Args:
            source: Ranking source

        Returns:
            List of division names
        """
        query = (
            select(FighterRanking.division)
            .where(FighterRanking.source == source)
            .distinct()
            .order_by(FighterRanking.division)
        )

        result = await self.session.execute(query)
        return [row[0] for row in result.all()]

    async def get_latest_ranking_date(
        self, source: str = "ufc"
    ) -> date | None:
        """Get the most recent ranking date in the database.

        Args:
            source: Ranking source

        Returns:
            Most recent ranking date or None
        """
        query = (
            select(func.max(FighterRanking.rank_date))
            .where(FighterRanking.source == source)
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    def _calculate_rank_movement(
        self, current_rank: int | None, previous_rank: int | None
    ) -> int:
        """Calculate rank movement (positive = moved up, negative = moved down).

        Args:
            current_rank: Current rank (0=Champion, 1-15)
            previous_rank: Previous rank

        Returns:
            Movement delta (e.g., +2 means moved up 2 spots)
        """
        if current_rank is None or previous_rank is None:
            return 0

        # Lower rank number = better, so movement is inverted
        # Moving from #5 to #3 = +2 (moved up 2 spots)
        return previous_rank - current_rank
