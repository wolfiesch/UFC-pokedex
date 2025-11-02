from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Literal

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import get_db
from backend.db.repositories import PostgreSQLFighterRepository
from backend.schemas.fighter import FighterDetail, FighterListItem
from backend.schemas.stats import (
    LeaderboardsResponse,
    MetricLeaderboard,
    TrendsResponse,
)


class FighterRepositoryProtocol:
    async def list_fighters(
        self, *, limit: int | None = None, offset: int | None = None
    ) -> Iterable[FighterListItem]:
        """Return lightweight fighter listings honoring pagination hints."""

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Retrieve a single fighter with rich detail by unique identifier."""

    async def stats_summary(self) -> dict[str, float]:
        """Provide high-level metrics describing the indexed roster."""

    async def get_leaderboards(
        self,
        *,
        limit: int,
        accuracy_metric: str,
        submissions_metric: str,
        start_date: date | None,
        end_date: date | None,
    ) -> LeaderboardsResponse:
        """Generate leaderboard slices for accuracy- and submission-oriented metrics."""

    async def get_trends(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        time_bucket: Literal["month", "quarter", "year"],
        streak_limit: int,
    ) -> TrendsResponse:
        """Summarize longitudinal streaks and fight duration trends within the roster."""


class InMemoryFighterRepository(FighterRepositoryProtocol):
    """Temporary repository used until database layer is implemented."""

    def __init__(self) -> None:
        self._fighters = {
            "sample-fighter": FighterDetail(
                fighter_id="sample-fighter",
                name="Sample Fighter",
                nickname="Prototype",
                height="6'0\"",
                weight="170 lbs.",
                reach='74"',
                stance="Orthodox",
                dob=date(1990, 1, 1),
                record="10-2-0",
                striking={"sig_strikes_landed_per_min": 3.5},
                grappling={"takedown_accuracy": "45%"},
                fight_history=[],
            )
        }

    async def list_fighters(self) -> Iterable[FighterListItem]:
        return list(self._fighters.values())

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        return self._fighters.get(fighter_id)

    async def stats_summary(self) -> dict[str, float]:
        return {"fighters_indexed": float(len(self._fighters))}

    async def get_leaderboards(
        self,
        *,
        limit: int,
        accuracy_metric: str,
        submissions_metric: str,
        start_date: date | None,
        end_date: date | None,
    ) -> LeaderboardsResponse:
        """Return empty leaderboard shells for the in-memory prototype repository."""

        return LeaderboardsResponse(
            accuracy=MetricLeaderboard(metric=accuracy_metric, entries=[]),
            submissions=MetricLeaderboard(metric=submissions_metric, entries=[]),
        )

    async def get_trends(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        time_bucket: Literal["month", "quarter", "year"],
        streak_limit: int,
    ) -> TrendsResponse:
        """Return empty trend payloads for the in-memory prototype repository."""

        return TrendsResponse()


class FighterService:
    def __init__(
        self, repository: FighterRepositoryProtocol | PostgreSQLFighterRepository
    ) -> None:
        self._repository = repository

    async def list_fighters(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[FighterListItem]:
        """Return paginated fighter summaries from the backing repository."""

        fighters = await self._repository.list_fighters(limit=limit, offset=offset)
        return list(fighters)

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Fetch a single fighter profile including detailed statistics."""

        return await self._repository.get_fighter(fighter_id)

    async def get_stats_summary(self) -> dict[str, float]:
        """Expose system-level counts such as fighters indexed for dashboards."""

        return await self._repository.stats_summary()

    async def count_fighters(self) -> int:
        """Get the total count of fighters."""
        if hasattr(self._repository, "count_fighters"):
            return await self._repository.count_fighters()
        else:
            # Fallback for repositories without count
            fighters = await self._repository.list_fighters()
            return len(list(fighters))

    async def get_random_fighter(self) -> FighterListItem | None:
        """Get a random fighter."""
        if hasattr(self._repository, "get_random_fighter"):
            return await self._repository.get_random_fighter()
        else:
            # Fallback for repositories without random
            import random

            fighters = await self._repository.list_fighters()
            fighter_list = list(fighters)
            if not fighter_list:
                return None
            return random.choice(fighter_list)

    async def search_fighters(
        self, query: str | None = None, stance: str | None = None
    ) -> list[FighterListItem]:
        """Search fighters by name or filter by stance."""
        if hasattr(self._repository, "search_fighters"):
            fighters = await self._repository.search_fighters(
                query=query, stance=stance
            )
            return list(fighters)
        else:
            # Fallback for repositories that don't support search natively.
            fighters = await self._repository.list_fighters()
            query_lower = query.lower() if query else None
            stance_lower = stance.lower() if stance else None
            filtered: list[FighterListItem] = []
            for fighter in fighters:
                name_match = True
                if query_lower:
                    name_parts = [
                        getattr(fighter, "name", "") or "",
                        getattr(fighter, "nickname", "") or "",
                    ]
                    haystack = " ".join(part for part in name_parts if part).lower()
                    name_match = query_lower in haystack
                stance_match = True
                if stance_lower:
                    fighter_stance = (getattr(fighter, "stance", None) or "").lower()
                    stance_match = fighter_stance == stance_lower
                if name_match and stance_match:
                    filtered.append(fighter)
            return filtered

    async def get_leaderboards(
        self,
        *,
        limit: int = 10,
        accuracy_metric: str = "sig_strikes_accuracy_pct",
        submissions_metric: str = "avg_submissions",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> LeaderboardsResponse:
        """Surface aggregated leaderboards for accuracy- and submission-based metrics."""

        return await self._repository.get_leaderboards(
            limit=limit,
            accuracy_metric=accuracy_metric,
            submissions_metric=submissions_metric,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_trends(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        time_bucket: Literal["month", "quarter", "year"] = "month",
        streak_limit: int = 5,
    ) -> TrendsResponse:
        """Provide historical streaks and fight duration trends for analytics dashboards."""

        return await self._repository.get_trends(
            start_date=start_date,
            end_date=end_date,
            time_bucket=time_bucket,
            streak_limit=streak_limit,
        )


def get_fighter_service(session: AsyncSession = Depends(get_db)) -> FighterService:
    """FastAPI dependency that provides FighterService with PostgreSQL repository."""
    repository = PostgreSQLFighterRepository(session)
    return FighterService(repository)
