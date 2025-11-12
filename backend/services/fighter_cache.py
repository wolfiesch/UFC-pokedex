"""Caching utilities and mixins for fighter query workflows."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any, Literal

from pydantic import ValidationError

from backend.cache import CacheClient, comparison_key, detail_key, list_key, search_key
from backend.db.repositories.fighter_repository import FighterSearchFilters
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
    nationality: str | None,
    include_streak: bool,
    streak_window: int,
) -> str | None:
    """Return a cache key for list endpoints when pagination hints are valid."""

    if limit is None or offset is None or limit < 0 or offset < 0:
        return None
    return list_key(
        limit,
        offset,
        nationality=nationality,
        include_streak=include_streak,
        streak_window=streak_window,
    )


def _should_cache_location_filtered(
    *,
    birthplace_country: str | None,
    birthplace_city: str | None,
    training_country: str | None,
    training_city: str | None,
    training_gym: str | None,
    has_location_data: bool | None,
) -> bool:
    """Return ``True`` when caching is safe for location parameters."""

    return not any(
        [
            birthplace_country,
            birthplace_city,
            training_country,
            training_city,
            training_gym,
            has_location_data,
        ]
    )


def _list_cache_resolver(
    _self: FighterQueryCacheMixin,
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
) -> str | None:
    """Return a list cache key while avoiding location-filtered entries."""

    if not _should_cache_location_filtered(
        birthplace_country=birthplace_country,
        birthplace_city=birthplace_city,
        training_country=training_country,
        training_city=training_city,
        training_gym=training_gym,
        has_location_data=has_location_data,
    ):
        return None
    return _list_cache_key(
        limit=limit,
        offset=offset,
        nationality=nationality,
        include_streak=include_streak,
        streak_window=streak_window,
    )


def _count_cache_resolver(
    _self: FighterQueryCacheMixin,
    *,
    nationality: str | None = None,
    birthplace_country: str | None = None,
    birthplace_city: str | None = None,
    training_country: str | None = None,
    training_city: str | None = None,
    training_gym: str | None = None,
    has_location_data: bool | None = None,
) -> str | None:
    """Return a count cache key or ``None`` when caching is unsafe."""

    if not _should_cache_location_filtered(
        birthplace_country=birthplace_country,
        birthplace_city=birthplace_city,
        training_country=training_country,
        training_city=training_city,
        training_gym=training_gym,
        has_location_data=has_location_data,
    ):
        return None
    scope = nationality if nationality else "all"
    return f"fighters:count:{scope}"


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


class FighterQueryCacheMixin(CacheableService):
    """Thin mixin encapsulating cache orchestration for fighter queries."""

    def __init__(self, *, cache: CacheClient | None = None) -> None:
        """Store the cache client while keeping subclasses focused on repositories."""

        super().__init__(cache=cache)

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
        """Delegate to the repository and return materialised fighter rows."""

        raise NotImplementedError

    @cached(
        _list_cache_resolver,
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
        """Return paginated fighter summaries with cache assistance."""

        return await self._list_fighters_impl(
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

    async def _get_fighter_impl(self, fighter_id: str) -> FighterDetail | None:
        """Retrieve a single fighter detail from the data store."""

        raise NotImplementedError

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

        return await self._get_fighter_impl(fighter_id)

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
        """Count roster entries given optional metadata filters."""

        raise NotImplementedError

    @cached(
        _count_cache_resolver,
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

        return await self._count_fighters_impl(
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
        """Collect comparison-ready fighter snapshots."""

        raise NotImplementedError

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
        self,
        fighter_ids: Sequence[str],
    ) -> list[FighterComparisonEntry]:
        """Retrieve comparable stat bundles for the requested fighters."""

        return await self._compare_fighters_impl(fighter_ids)

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
        """Prepare normalized fighter search filters."""

        raise NotImplementedError

    async def _execute_search(
        self,
        *,
        filters: FighterSearchFilters,
        include_locations: bool,
        include_streak: bool,
        limit: int,
        offset: int,
    ) -> PaginatedFightersResponse:
        """Invoke the repository to perform the actual search query."""

        raise NotImplementedError

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

        filters = self._build_search_filters(
            query=query,
            stance=stance,
            division=division,
            champion_statuses=champion_statuses,
            streak_type=streak_type,
            min_streak_count=min_streak_count,
        )

        # Only persist cached results when filters produce deterministic subsets.
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

        response = await self._execute_search(
            filters=filters,
            include_locations=include_locations,
            include_streak=include_streak,
            limit=resolved_limit,
            offset=resolved_offset,
        )

        if cache_key is not None:
            await self._cache_set(cache_key, response.model_dump(), ttl=300)

        return response


__all__ = [
    "FighterQueryCacheMixin",
    "_deserialize_comparisons",
    "_deserialize_fighter_detail",
    "_deserialize_fighter_list",
    "_deserialize_search_results",
    "_list_cache_key",
    "_search_cache_key",
]
