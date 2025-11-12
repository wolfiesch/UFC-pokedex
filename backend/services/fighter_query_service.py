"""Read-model oriented fighter service with focused responsibilities."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Literal, Protocol, runtime_checkable

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import CacheClient, get_cache_client
from backend.db.connection import get_db
from backend.db.repositories.fighter_repository import (
    FighterRepository,
    FighterSearchFilters,
    normalize_search_filters,
)
from backend.schemas.fighter import (
    FighterComparisonEntry,
    FighterDetail,
    FighterListItem,
    PaginatedFightersResponse,
)
from backend.services.fighter_cache import FighterQueryCacheMixin


@runtime_checkable
class FighterRepositoryProtocol(Protocol):
    """Minimal repository surface required by :class:`FighterQueryService`."""

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
        """Return lightweight fighter listings honouring pagination hints."""

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Retrieve a single fighter with rich detail by unique identifier."""

    async def search_fighters(
        self,
        *,
        query: str | None = None,
        stance: str | None = None,
        division: str | None = None,
        champion_statuses: list[str] | None = None,
        streak_type: Literal["win", "loss"] | None = None,
        min_streak_count: int | None = None,
        include_locations: bool = True,
        include_streak: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[list[FighterListItem], int]:
        """Search roster entries using optional fighter metadata filters."""

    async def get_fighters_for_comparison(
        self, fighter_ids: Sequence[str]
    ) -> list[FighterComparisonEntry]:
        """Return stat snapshots for the provided fighter identifiers."""

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
        """Return the total number of indexed fighters (optionally filtered)."""

    async def get_random_fighter(self) -> FighterListItem | None:
        """Return a random fighter suitable for roster teasers."""


class FighterQueryService(FighterQueryCacheMixin):
    """Service focused on read-model fighter operations with caching support."""

    def __init__(
        self,
        repository: FighterRepositoryProtocol,
        *,
        cache: CacheClient | None = None,
    ) -> None:
        super().__init__(cache=cache)
        self._repository = repository

    async def _list_fighters_impl(
        self,
        *,
        limit: int | None,
        offset: int | None,
        nationality: str | None,
        birthplace_country: str | None,
        birthplace_city: str | None,
        training_country: str | None,
        training_city: str | None,
        training_gym: str | None,
        has_location_data: bool | None,
        include_streak: bool,
        streak_window: int,
    ) -> list[FighterListItem]:
        """Materialise roster entries from the repository for caching."""

        fighters = await self._repository.list_fighters(
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
        return list(fighters)

    async def _get_fighter_impl(self, fighter_id: str) -> FighterDetail | None:
        """Proxy detailed fighter retrieval to the repository."""

        return await self._repository.get_fighter(fighter_id)

    async def _count_fighters_impl(
        self,
        *,
        nationality: str | None,
        birthplace_country: str | None,
        birthplace_city: str | None,
        training_country: str | None,
        training_city: str | None,
        training_gym: str | None,
        has_location_data: bool | None,
    ) -> int:
        """Delegate fighter counting to the repository."""

        return await self._repository.count_fighters(
            nationality=nationality,
            birthplace_country=birthplace_country,
            birthplace_city=birthplace_city,
            training_country=training_country,
            training_city=training_city,
            training_gym=training_gym,
            has_location_data=has_location_data,
        )

    async def _compare_fighters_impl(
        self,
        fighter_ids: Sequence[str],
    ) -> list[FighterComparisonEntry]:
        """Delegate comparison retrieval to the repository."""

        return await self._repository.get_fighters_for_comparison(fighter_ids)

    def _build_search_filters(
        self,
        *,
        query: str | None,
        stance: str | None,
        division: str | None,
        champion_statuses: list[str] | None,
        streak_type: Literal["win", "loss"] | None,
        min_streak_count: int | None,
    ) -> FighterSearchFilters:
        """Normalize user-provided search parameters before caching."""

        return normalize_search_filters(
            query=query,
            stance=stance,
            division=division,
            champion_statuses=champion_statuses,
            streak_type=streak_type,
            min_streak_count=min_streak_count,
        )

    async def _execute_search(
        self,
        *,
        filters: FighterSearchFilters,
        include_locations: bool,
        include_streak: bool,
        limit: int,
        offset: int,
    ) -> PaginatedFightersResponse:
        """Execute the repository search and craft the paginated response."""

        fighters, total = await self._repository.search_fighters(
            query=filters.query,
            stance=filters.stance,
            division=filters.division,
            champion_statuses=(
                list(filters.champion_statuses) if filters.champion_statuses else None
            ),
            streak_type=filters.streak_type,
            min_streak_count=filters.min_streak_count,
            include_locations=include_locations,
            include_streak=include_streak,
            limit=limit,
            offset=offset,
        )

        has_more = offset + len(fighters) < total
        return PaginatedFightersResponse(
            fighters=fighters,
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more,
        )

    async def get_random_fighter(self) -> FighterListItem | None:
        """Return a random fighter without caching (high variance by design)."""

        return await self._repository.get_random_fighter()


def get_fighter_query_service(
    session: AsyncSession = Depends(get_db),
    cache: CacheClient = Depends(get_cache_client),
) -> FighterQueryService:
    """FastAPI dependency wiring the repository and cache for queries."""

    repository = FighterRepository(session)
    return FighterQueryService(repository, cache=cache)


__all__ = [
    "FighterQueryService",
    "FighterRepositoryProtocol",
    "get_fighter_query_service",
]
