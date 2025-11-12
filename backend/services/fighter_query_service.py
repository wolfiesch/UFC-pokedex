"""Read-model oriented fighter service with focused responsibilities."""

from __future__ import annotations

import logging
import secrets
from collections.abc import Iterable, Sequence
from datetime import date
from typing import Literal, Protocol, runtime_checkable

from pydantic import ValidationError

from backend.cache import CacheClient
from backend.db.repositories.fighter_repository import (
    FighterRepository,
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
from backend.services.fighter_cache import (
    FIGHTER_COMPARISON_TTL,
    FIGHTER_DETAIL_TTL,
    FIGHTER_LIST_TTL,
    FIGHTER_SEARCH_TTL,
    deserialize_fighter_comparisons,
    deserialize_fighter_detail,
    deserialize_fighter_list,
    deserialize_fighter_search,
    fighter_comparison_cache_key,
    fighter_detail_cache_key,
    fighter_list_cache_key,
    fighter_search_cache_key,
    serialize_fighter_comparisons,
    serialize_fighter_detail,
    serialize_fighter_list,
    serialize_fighter_search,
)

logger = logging.getLogger(__name__)


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
        lambda _self, *, limit=None, offset=None, nationality=None, birthplace_country=None, birthplace_city=None, training_country=None, training_city=None, training_gym=None, has_location_data=None, include_streak=False, streak_window=6: (
            fighter_list_cache_key(
                limit=limit,
                offset=offset,
                nationality=nationality,
                include_streak=include_streak,
                streak_window=streak_window,
            )
            if not any(
                [
                    birthplace_country,
                    birthplace_city,
                    training_country,
                    training_city,
                    training_gym,
                    has_location_data,
                ]
            )
            else None
        ),  # Don't cache location-filtered queries for now
        ttl=FIGHTER_LIST_TTL,
        serializer=serialize_fighter_list,
        deserializer=deserialize_fighter_list,
        deserialize_error_message=(
            "Failed to deserialize cached fighter list for key {key}: {error}"
        ),
    )
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
    ) -> list[FighterListItem]:
        """Return paginated fighter summaries from the backing repository."""

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

    @cached(
        lambda _self, fighter_id: fighter_detail_cache_key(fighter_id),
        ttl=FIGHTER_DETAIL_TTL,
        serializer=serialize_fighter_detail,
        deserializer=deserialize_fighter_detail,
        deserialize_error_message=(
            "Failed to deserialize cached fighter detail for key {key}: {error}"
        ),
    )
    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Fetch a single fighter profile including detailed statistics."""

        return await self._repository.get_fighter(fighter_id)

    @cached(
        lambda _self, nationality=None, birthplace_country=None, birthplace_city=None, training_country=None, training_city=None, training_gym=None, has_location_data=None: (
            f"fighters:count:{nationality if nationality else 'all'}"
            if not any(
                [
                    birthplace_country,
                    birthplace_city,
                    training_country,
                    training_city,
                    training_gym,
                    has_location_data,
                ]
            )
            else None
        ),  # Don't cache location-filtered counts
        ttl=600,
    )
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
        """Return the total number of indexed fighters with caching (optionally filtered)."""

        return await self._repository.count_fighters(
            nationality=nationality,
            birthplace_country=birthplace_country,
            birthplace_city=birthplace_city,
            training_country=training_country,
            training_city=training_city,
            training_gym=training_gym,
            has_location_data=has_location_data,
        )

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
        include_locations: bool = True,
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
            fighter_search_cache_key(
                filters,
                limit=resolved_limit,
                offset=resolved_offset,
            )
            if should_cache
            else None
        )

        if cache_key is not None:
            cached_payload = await self._cache_get(cache_key)
            if cached_payload is not None:
                try:
                    return deserialize_fighter_search(cached_payload)
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
            include_locations=include_locations,
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
            await self._cache_set(
                cache_key,
                serialize_fighter_search(response),
                ttl=FIGHTER_SEARCH_TTL,
            )

        return response

    @cached(
        lambda _self, fighter_ids: fighter_comparison_cache_key(fighter_ids),
        ttl=FIGHTER_COMPARISON_TTL,
        serializer=serialize_fighter_comparisons,
        deserializer=deserialize_fighter_comparisons,
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
        """Return fighters in insertion order while honouring pagination hints."""

        roster: list[FighterListItem] = [
            self._list_item_from_detail(detail) for detail in self._fighters.values()
        ]
        # Apply nationality filter if specified
        if nationality:
            roster = [f for f in roster if f.nationality == nationality]
        # Add location filters (simple implementation for in-memory)
        if birthplace_country:
            roster = [f for f in roster if f.birthplace_country == birthplace_country]
        if training_gym:
            roster = [
                f
                for f in roster
                if f.training_gym and training_gym.lower() in f.training_gym.lower()
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
        include_locations: bool = True,
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
                    record=detail.record,
                    division=detail.division,
                    striking=detail.striking,
                    grappling=detail.grappling,
                    significant_strikes=getattr(detail, "significant_strikes", {}),
                    takedown_stats=getattr(detail, "takedown_stats", {}),
                    career={},
                )
            )
        return fighters

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
        # Simple implementation for in-memory repository
        if nationality:
            return sum(
                1
                for detail in self._fighters.values()
                if getattr(detail, "nationality", None) == nationality
            )
        return len(self._fighters)

    async def get_random_fighter(self) -> FighterListItem | None:
        if not self._fighters:
            return None
        fighter_id = secrets.choice(list(self._fighters.keys()))
        detail = self._fighters[fighter_id]
        return self._list_item_from_detail(detail)


__all__ = [
    "FighterQueryService",
    "FighterRepositoryProtocol",
    "InMemoryFighterRepository",
]
