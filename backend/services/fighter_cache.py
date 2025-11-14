"""Cache helper utilities shared by fighter-oriented services.

This module centralises cache key generation, serialisation, and deserialisation
for fighter list, detail, search, and comparison responses.  By colocating the
logic here we ensure the :class:`~backend.services.fighter_query_service.FighterQueryService`
remains focused on orchestrating repository access while cache policy is defined
in a single location.

The helpers are intentionally verbose with documentation so that future changes
(e.g. TTL adjustments or schema tweaks) are easier to reason about without
having to dive into multiple modules.  All functions provide explicit type hints
which improves static analysis and IDE support.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from backend.cache import comparison_key, detail_key, list_key, search_key
from backend.db.repositories.fighter_repository import FighterSearchFilters
from backend.schemas.fighter import (
    FighterComparisonEntry,
    FighterDetail,
    FighterListItem,
    PaginatedFightersResponse,
)

# ---------------------------------------------------------------------------
# TTL constants
# ---------------------------------------------------------------------------
# Using descriptive names for TTLs makes their intent obvious in the service
# layer while still allowing centralised updates.
FIGHTER_LIST_TTL: int = 300
FIGHTER_DETAIL_TTL: int = 7200
FIGHTER_SEARCH_TTL: int = 300
FIGHTER_COMPARISON_TTL: int = 600


# ---------------------------------------------------------------------------
# Fighter list cache helpers
# ---------------------------------------------------------------------------
def fighter_list_cache_key(
    *,
    limit: int | None,
    offset: int | None,
    nationality: str | None,
    include_streak: bool,
    streak_window: int,
) -> str | None:
    """Build a cache key for fighter list responses.

    The list endpoint only caches when both ``limit`` and ``offset`` are
    provided with non-negative values.  Location filters are handled at the
    service layer because their combinations can explode the cache cardinality.
    """

    if limit is None or offset is None or limit < 0 or offset < 0:
        return None
    return list_key(
        limit,
        offset,
        nationality=nationality,
        include_streak=include_streak,
        streak_window=streak_window,
    )


def serialize_fighter_list(fighters: Iterable[FighterListItem]) -> list[dict[str, Any]]:
    """Serialise fighters into cache friendly dictionaries."""

    return [fighter.model_dump() for fighter in fighters]


def deserialize_fighter_list(payload: Any) -> list[FighterListItem]:
    """Rehydrate cached fighter list payloads back into Pydantic models."""

    if not isinstance(payload, list):
        raise TypeError("Expected cached fighter list to be a list")
    return [FighterListItem.model_validate(item) for item in payload]


# ---------------------------------------------------------------------------
# Fighter detail cache helpers
# ---------------------------------------------------------------------------
def fighter_detail_cache_key(fighter_id: str) -> str:
    """Return the canonical cache key for a fighter detail response."""

    return detail_key(fighter_id)


def serialize_fighter_detail(detail: FighterDetail) -> dict[str, Any]:
    """Serialise a fighter detail into a JSON compatible payload."""

    return detail.model_dump()


def deserialize_fighter_detail(payload: Any) -> FighterDetail:
    """Convert cached fighter detail payloads back into ``FighterDetail``."""

    if not isinstance(payload, dict):
        raise TypeError("Expected cached fighter detail to be a mapping")
    return FighterDetail.model_validate(payload)


# ---------------------------------------------------------------------------
# Fighter search cache helpers
# ---------------------------------------------------------------------------
def fighter_search_cache_key(
    filters: FighterSearchFilters,
    *,
    limit: int,
    offset: int,
) -> str:
    """Produce a deterministic cache key for fighter search responses."""

    champion_fragment = (
        ",".join(sorted(filters.champion_statuses))
        if filters.champion_statuses
        else None
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


def serialize_fighter_search(response: PaginatedFightersResponse) -> dict[str, Any]:
    """Serialise the paginated search response into cache safe JSON."""

    return response.model_dump()


def deserialize_fighter_search(payload: Any) -> PaginatedFightersResponse:
    """Reconstruct ``PaginatedFightersResponse`` from cached data."""

    if not isinstance(payload, dict):
        raise TypeError("Expected cached search payload to be a mapping")
    return PaginatedFightersResponse.model_validate(payload)


# ---------------------------------------------------------------------------
# Fighter comparison cache helpers
# ---------------------------------------------------------------------------
def fighter_comparison_cache_key(fighter_ids: Sequence[str]) -> str | None:
    """Return a cache key for fighter comparison payloads.

    Comparisons are only cached when at least two fighters are involved to avoid
    persisting partially filled bundles.
    """

    if len(fighter_ids) < 2:
        return None

    # ``comparison_key`` consumes the identifiers exactly as provided so that
    # callers requesting ``["alpha", "beta"]`` and ``["beta", "alpha"]``
    # persist independent cache entries.  This maintains the requested ordering
    # semantics when rehydrating cached payloads.
    return comparison_key(tuple(fighter_ids))


def serialize_fighter_comparisons(
    fighters: Iterable[FighterComparisonEntry],
) -> list[dict[str, Any]]:
    """Serialise fighter comparison entries for caching."""

    return [entry.model_dump() for entry in fighters]


def deserialize_fighter_comparisons(payload: Any) -> list[FighterComparisonEntry]:
    """Rehydrate cached comparison payloads into Pydantic models."""

    if not isinstance(payload, list):
        raise TypeError("Expected cached comparison payload to be a list")
    return [FighterComparisonEntry.model_validate(item) for item in payload]


__all__ = [
    "FIGHTER_COMPARISON_TTL",
    "FIGHTER_DETAIL_TTL",
    "FIGHTER_LIST_TTL",
    "FIGHTER_SEARCH_TTL",
    "deserialize_fighter_comparisons",
    "deserialize_fighter_detail",
    "deserialize_fighter_list",
    "deserialize_fighter_search",
    "fighter_comparison_cache_key",
    "fighter_detail_cache_key",
    "fighter_list_cache_key",
    "fighter_search_cache_key",
    "serialize_fighter_comparisons",
    "serialize_fighter_detail",
    "serialize_fighter_list",
    "serialize_fighter_search",
]
