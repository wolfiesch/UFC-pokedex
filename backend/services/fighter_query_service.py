"""Read-model oriented fighter service with focused responsibilities."""

from __future__ import annotations

import logging
import secrets
from collections.abc import Iterable, Sequence
from datetime import date
from typing import Any, Literal, Protocol, runtime_checkable

from fastapi import Depends
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import (
    CacheClient,
    comparison_key,
    detail_key,
    get_cache_client,
    list_key,
    search_key,
)
from backend.db.connection import get_db
from backend.db.repositories.fighter_repository import (
    FighterRepository,
    FighterSearchFilters,
    filter_roster_entries,
    normalize_search_filters,
    paginate_roster_entries,
)
from backend.schemas.fighter import (
    FighterComparisonEntry,
    FighterDetail,
    FighterListItem,
    PaginatedFightersResponse,
)
from backend.services.caching import CacheableService, cached

logger = logging.getLogger(__name__)


def _list_cache_key(
    *,
    limit: int | None,
    offset: int | None,
    include_streak: bool,
    streak_window: int,
) -> str | None:
    """Return a cache key for list endpoints when pagination hints are valid."""

    if limit is None or offset is None or limit < 0 or offset < 0:
        return None
    return list_key(
        limit,
        offset,
        include_streak=include_streak,
        streak_window=streak_window,
    )


def _deserialize_fighter_list(payload: Any) -> list[FighterListItem]:
    """Deserialize cached fighter list payloads back into Pydantic models."""

    if not isinstance(payload, list):
        raise TypeError("Expected cached fighter list to be a list")
    return [FighterListItem.model_validate(item) for item in payload]


def _deserialize_fighter_detail(payload: Any) -> FighterDetail:
    """Deserialize cached fighter detail payloads back into rich models."""

    if not isinstance(payload, dict):
        raise TypeError("Expected cached fighter detail to be a mapping")
    return FighterDetail.model_validate(payload)


def _deserialize_search_results(payload: Any) -> PaginatedFightersResponse:
    """Deserialize cached search payloads into the paginated response model."""

    if not isinstance(payload, dict):
        raise TypeError("Expected cached search payload to be a mapping")
    return PaginatedFightersResponse.model_validate(payload)


def _deserialize_comparisons(payload: Any) -> list[FighterComparisonEntry]:
    """Deserialize cached fighter comparison payloads into entry models."""

    if not isinstance(payload, list):
        raise TypeError("Expected cached comparison payload to be a list")
    return [FighterComparisonEntry.model_validate(item) for item in payload]


def _search_cache_key(filters: FighterSearchFilters, *, limit: int, offset: int) -> str:
    """Return a deterministic cache key for fighter search results."""

    champion_fragment = (
        ",".join(filters.champion_statuses) if filters.champion_statuses else None
    )
    return search_key(
        query=filters.query or "",
        stance=filters.stance,
        division=filters.division,
        champion_statuses=champion_fragment,
        streak_type=filters.streak_type,
        min_streak_count=filters.min_streak_count,
        limit=limit,
        offset=offset,
    )


@runtime_checkable
class FighterRepositoryProtocol(Protocol):
    """Minimal repository surface required by :class:`FighterQueryService`."""

    async def list_fighters(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
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
        include_streak: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[list[FighterListItem], int]:
        """Search roster entries using optional fighter metadata filters."""

    async def get_fighters_for_comparison(
        self, fighter_ids: Sequence[str]
    ) -> list[FighterComparisonEntry]:
        """Return stat snapshots for the provided fighter identifiers."""

    async def count_fighters(self) -> int:
        """Return the total number of indexed fighters."""

    async def get_random_fighter(self) -> FighterListItem | None:
        """Return a random fighter suitable for roster teasers."""


class FighterQueryService(CacheableService):
    """Service focused on read-model fighter operations with caching support."""

    def __init__(
        self,
        repository: FighterRepositoryProtocol,
        *,
        cache: CacheClient | None = None,
    ) -> None:
        super().__init__(cache=cache)
        self._repository = repository

    @cached(
        lambda _self, *, limit=None, offset=None, include_streak=False, streak_window=6: _list_cache_key(
            limit=limit,
            offset=offset,
            include_streak=include_streak,
            streak_window=streak_window,
        ),
        ttl=300,
        serializer=lambda fighters: [fighter.model_dump() for fighter in fighters],
        deserializer=_deserialize_fighter_list,
        deserialize_error_message=(
            "Failed to deserialize cached fighter list for key {key}: {error}"
        ),
    )
    async def list_fighters(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        include_streak: bool = False,
        streak_window: int = 6,
    ) -> list[FighterListItem]:
        """Return paginated fighter summaries from the backing repository."""

        fighters = await self._repository.list_fighters(
            limit=limit,
            offset=offset,
            include_streak=include_streak,
            streak_window=streak_window,
        )
        return list(fighters)

    @cached(
        lambda _self, fighter_id: detail_key(fighter_id),
        ttl=7200,
        serializer=lambda fighter: fighter.model_dump(),
        deserializer=_deserialize_fighter_detail,
        deserialize_error_message=(
            "Failed to deserialize cached fighter detail for key {key}: {error}"
        ),
    )
    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Fetch a single fighter profile including detailed statistics."""

        return await self._repository.get_fighter(fighter_id)

    @cached(
        lambda _self: "fighters:count",
        ttl=600,
    )
    async def count_fighters(self) -> int:
        """Return the total number of indexed fighters with caching."""

        return await self._repository.count_fighters()

    async def get_random_fighter(self) -> FighterListItem | None:
        """Return a random fighter without caching (high variance by design)."""

        return await self._repository.get_random_fighter()

    async def search_fighters(
        self,
        *,
        query: str | None = None,
        stance: str | None = None,
        division: str | None = None,
        champion_statuses: list[str] | None = None,
        streak_type: Literal["win", "loss"] | None = None,
        min_streak_count: int | None = None,
        include_streak: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> PaginatedFightersResponse:
        """Search fighters by name, stance, division, champion status, or streak."""

        resolved_limit = limit if limit is not None and limit > 0 else 20
        resolved_offset = offset if offset is not None and offset >= 0 else 0

        filters = normalize_search_filters(
            query=query,
            stance=stance,
            division=division,
            champion_statuses=champion_statuses,
            streak_type=streak_type,
            min_streak_count=min_streak_count,
        )

        should_cache = any(
            (
                filters.query,
                filters.stance,
                filters.division,
                filters.champion_statuses,
                filters.streak_type,
            )
        )

        cache_key = (
            _search_cache_key(filters, limit=resolved_limit, offset=resolved_offset)
            if should_cache
            else None
        )

        if cache_key is not None:
            cached_payload = await self._cache_get(cache_key)
            if cached_payload is not None:
                try:
                    return _deserialize_search_results(cached_payload)
                except (ValidationError, TypeError) as exc:  # pragma: no cover
                    logger.warning(
                        "Failed to deserialize cached fighter search for key %s: %s",
                        cache_key,
                        exc,
                    )

        fighters, total = await self._repository.search_fighters(
            query=filters.query,
            stance=filters.stance,
            division=filters.division,
            champion_statuses=(
                list(filters.champion_statuses) if filters.champion_statuses else None
            ),
            streak_type=filters.streak_type,
            min_streak_count=filters.min_streak_count,
            include_streak=include_streak,
            limit=resolved_limit,
            offset=resolved_offset,
        )

        has_more = resolved_offset + len(fighters) < total
        response = PaginatedFightersResponse(
            fighters=fighters,
            total=total,
            limit=resolved_limit,
            offset=resolved_offset,
            has_more=has_more,
        )

        if cache_key is not None:
            await self._cache_set(cache_key, response.model_dump(), ttl=300)

        return response

    @cached(
        lambda _self, fighter_ids: (
            comparison_key(fighter_ids) if len(fighter_ids) >= 2 else None
        ),
        ttl=600,
        serializer=lambda fighters: [entry.model_dump() for entry in fighters],
        deserializer=_deserialize_comparisons,
        deserialize_error_message=(
            "Failed to deserialize cached fighter comparison for key {key}: {error}"
        ),
    )
    async def compare_fighters(
        self, fighter_ids: Sequence[str]
    ) -> list[FighterComparisonEntry]:
        """Retrieve comparable stat bundles for the requested fighters."""

        return await self._repository.get_fighters_for_comparison(fighter_ids)


class InMemoryFighterRepository(FighterRepositoryProtocol):
    """Temporary repository used in tests and during local development."""

    def __init__(self) -> None:
        self._fighters = {
            "sample-fighter": FighterDetail(
                fighter_id="sample-fighter",
                detail_url="http://www.ufcstats.com/fighter-details/sample-fighter",
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

    def _list_item_from_detail(self, detail: FighterDetail) -> FighterListItem:
        """Convert a stored fighter detail into a lightweight list item."""

        return FighterListItem.model_validate(detail.model_dump())

    async def list_fighters(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        include_streak: bool = False,
        streak_window: int = 6,
    ) -> Iterable[FighterListItem]:
        """Return fighters in insertion order while honouring pagination hints."""

        roster: list[FighterListItem] = [
            self._list_item_from_detail(detail) for detail in self._fighters.values()
        ]
        return paginate_roster_entries(
            roster,
            limit=limit,
            offset=offset,
        )

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        return self._fighters.get(fighter_id)

    async def search_fighters(
        self,
        *,
        query: str | None = None,
        stance: str | None = None,
        division: str | None = None,
        champion_statuses: list[str] | None = None,
        streak_type: Literal["win", "loss"] | None = None,
        min_streak_count: int | None = None,
        include_streak: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[list[FighterListItem], int]:
        filters = normalize_search_filters(
            query=query,
            stance=stance,
            division=division,
            champion_statuses=champion_statuses,
            streak_type=streak_type,
            min_streak_count=min_streak_count,
        )

        roster = [
            self._list_item_from_detail(detail) for detail in self._fighters.values()
        ]
        filtered = filter_roster_entries(roster, filters=filters)
        paginated = list(
            paginate_roster_entries(
                filtered,
                limit=limit,
                offset=offset,
            )
        )
        return paginated, len(filtered)

    async def get_fighters_for_comparison(
        self, fighter_ids: Sequence[str]
    ) -> list[FighterComparisonEntry]:
        fighters: list[FighterComparisonEntry] = []
        for fighter_id in fighter_ids:
            detail = self._fighters.get(fighter_id)
            if detail is None:
                continue
            fighters.append(
                FighterComparisonEntry(
                    fighter_id=fighter_id,
                    name=detail.name,
                )
            )
        return fighters

    async def count_fighters(self) -> int:
        return len(self._fighters)

    async def get_random_fighter(self) -> FighterListItem | None:
        if not self._fighters:
            return None
        fighter_id = secrets.choice(list(self._fighters.keys()))
        detail = self._fighters[fighter_id]
        return self._list_item_from_detail(detail)


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
    "InMemoryFighterRepository",
    "get_fighter_query_service",
]
