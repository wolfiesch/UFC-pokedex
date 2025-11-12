"""Backward compatibility facade for fighter-related repositories.

This module preserves the original ``PostgreSQLFighterRepository`` interface
by delegating to the new, focused repository implementations. Existing code
continues to work without modification.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Fight, Fighter
from backend.db.repositories.fight_graph_repository import FightGraphRepository
from backend.db.repositories.fight_repository import FightRepository
from backend.db.repositories.fighter_repository import FighterRepository
from backend.db.repositories.stats_repository import StatsRepository
from backend.schemas.fight_graph import FightGraphResponse
from backend.schemas.fighter import (
    FighterComparisonEntry,
    FighterDetail,
    FighterListItem,
)
from backend.schemas.stats import (
    LeaderboardMetricId,
    LeaderboardsResponse,
    StatsSummaryResponse,
    TrendTimeBucket,
    TrendsResponse,
)
from backend.services.fighter_presentation_service import FighterPresentationService


class PostgreSQLFighterRepository:
    """Facade delegating to specialized repositories for fighter operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._fighter_repo = FighterRepository(session)
        self._presentation = FighterPresentationService(self._fighter_repo)
        self._fight_graph_repo = FightGraphRepository(session)
        self._stats_repo = StatsRepository(session)
        self._fight_repo = FightRepository(session)

    # Fighter operations - delegate to FighterRepository
    async def list_fighters(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        nationality: str | None = None,
        birthplace_country: str | None = None,
        birthplace_city: str | None = None,
        training_country: str | None = None,
        training_city: str | None = None,
        training_gym: str | None = None,
        has_location_data: bool | None = None,
        include_streak: bool = False,
        streak_window: int = 6,
    ) -> Iterable[FighterListItem]:
        """List all fighters with optional pagination."""
        return await self._presentation.list_fighters(
            limit=limit,
            offset=offset,
            nationality=nationality,
            birthplace_country=birthplace_country,
            birthplace_city=birthplace_city,
            training_country=training_country,
            training_city=training_city,
            training_gym=training_gym,
            has_location_data=has_location_data,
            include_streak=include_streak,
            streak_window=streak_window,
        )

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Get detailed fighter information by ID."""
        return await self._presentation.get_fighter(fighter_id)

    async def search_fighters(
        self,
        query: str | None = None,
        stance: str | None = None,
        division: str | None = None,
        champion_statuses: list[str] | None = None,
        streak_type: str | None = None,
        min_streak_count: int | None = None,
        include_streak: bool = False,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[list[FighterListItem], int]:
        """Search fighters by various criteria."""
        return await self._presentation.search_fighters(
            query=query,
            stance=stance,
            division=division,
            champion_statuses=champion_statuses,
            streak_type=streak_type,
            min_streak_count=min_streak_count,
            include_streak=include_streak,
            limit=limit,
            offset=offset,
        )

    async def get_fighters_for_comparison(
        self, fighter_ids: Sequence[str]
    ) -> list[FighterComparisonEntry]:
        """Return stats snapshots for the requested fighters."""
        return await self._presentation.get_fighters_for_comparison(fighter_ids)

    async def count_fighters(
        self,
        nationality: str | None = None,
        birthplace_country: str | None = None,
        birthplace_city: str | None = None,
        training_country: str | None = None,
        training_city: str | None = None,
        training_gym: str | None = None,
        has_location_data: bool | None = None,
    ) -> int:
        """Get the total count of fighters."""
        return await self._presentation.count_fighters(
            nationality=nationality,
            birthplace_country=birthplace_country,
            birthplace_city=birthplace_city,
            training_country=training_country,
            training_city=training_city,
            training_gym=training_gym,
            has_location_data=has_location_data,
        )

    async def get_random_fighter(self) -> FighterListItem | None:
        """Get a random fighter."""
        return await self._presentation.get_random_fighter()

    async def create_fighter(self, fighter: Fighter) -> Fighter:
        """Create a new fighter."""
        return await self._fighter_repo.create_fighter(fighter)

    async def upsert_fighter(self, fighter_data: dict) -> Fighter:
        """Insert or update a fighter."""
        return await self._fighter_repo.upsert_fighter(fighter_data)

    # Fight graph operations - delegate to FightGraphRepository
    async def get_fight_graph(
        self,
        *,
        division: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 200,
        include_upcoming: bool = False,
    ) -> FightGraphResponse:
        """Aggregate fighters and bout links for visualization."""
        return await self._fight_graph_repo.get_fight_graph(
            division=division,
            start_year=start_year,
            end_year=end_year,
            limit=limit,
            include_upcoming=include_upcoming,
        )

    # Stats operations - delegate to StatsRepository
    async def stats_summary(self) -> StatsSummaryResponse:
        """Get aggregate statistics about fighters."""
        return await self._stats_repo.stats_summary()

    async def get_leaderboards(
        self,
        *,
        limit: int,
        accuracy_metric: LeaderboardMetricId,
        submissions_metric: LeaderboardMetricId,
        start_date: date | None,
        end_date: date | None,
    ) -> LeaderboardsResponse:
        """Compute leaderboard slices."""
        return await self._stats_repo.get_leaderboards(
            limit=limit,
            accuracy_metric=accuracy_metric,
            submissions_metric=submissions_metric,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_trends(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        time_bucket: TrendTimeBucket,
        streak_limit: int,
    ) -> TrendsResponse:
        """Aggregate longitudinal trends."""
        return await self._stats_repo.get_trends(
            start_date=start_date,
            end_date=end_date,
            time_bucket=time_bucket,
            streak_limit=streak_limit,
        )

    # Fight operations - delegate to FightRepository
    async def create_fight(self, fight: Fight) -> Fight:
        """Create a new fight record."""
        return await self._fight_repo.create_fight(fight)
