from __future__ import annotations

import logging
from typing import Any

from backend.cache import CacheClient
from backend.db.repositories import PostgreSQLEventRepository
from backend.schemas.event import EventDetail, EventListItem, PaginatedEventsResponse
from backend.services.caching import CacheableService, cached

logger = logging.getLogger(__name__)


# Default cache lifetimes tuned for event volatility.
EVENT_LIST_TTL_SECONDS = 300
EVENT_DETAIL_TTL_SECONDS = 600


def _event_list_cache_key(
    _self: EventService,
    *,
    status: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> str | None:
    """Return the cache key for :meth:`EventService.list_events` invocations.

    The cache is only consulted when both ``limit`` and ``offset`` are explicit
    non-negative integers.  Queries that fall outside of that envelope tend to
    represent bespoke slices (e.g. UI widgets pulling full archives) and are
    therefore skipped to avoid polluting the shared cache namespace.
    """

    if limit is None or offset is None:
        return None
    if limit < 0 or offset < 0:
        return None
    normalised_status = status or "all"
    return f"events:list:status={normalised_status}:limit={limit}:offset={offset}"


def _serialize_event_list(events: list[EventListItem]) -> list[dict[str, Any]]:
    """Convert a list of event models into JSON-serialisable payloads."""

    return [event.model_dump() for event in events]


def _deserialize_event_list(payload: Any) -> list[EventListItem]:
    """Reconstruct cached event list entries into :class:`EventListItem` objects."""

    if not isinstance(payload, list):  # Defensive guard for corrupted cache entries
        raise TypeError("Cached event list payload must be a list of mappings")
    return [EventListItem.model_validate(item) for item in payload]


def _event_detail_cache_key(_self: EventService, event_id: str) -> str:
    """Return the cache key used for storing a single event detail payload."""

    return f"events:detail:{event_id}"


def _serialize_event_detail(event: EventDetail | None) -> dict[str, Any] | None:
    """Serialize event detail responses while preserving ``None`` semantics."""

    if event is None:
        return None
    return event.model_dump()


def _deserialize_event_detail(payload: Any) -> EventDetail | None:
    """Deserialize cached detail payloads back into :class:`EventDetail` objects."""

    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise TypeError("Cached event detail payload must be a mapping")
    return EventDetail.model_validate(payload)


class EventService(CacheableService):
    """Service layer for event operations with optional caching."""

    def __init__(
        self,
        repository: PostgreSQLEventRepository,
        cache: CacheClient | None = None,
    ) -> None:
        super().__init__(cache=cache)
        self._repository = repository

    @cached(
        _event_list_cache_key,
        ttl=EVENT_LIST_TTL_SECONDS,
        serializer=_serialize_event_list,
        deserializer=_deserialize_event_list,
        deserialize_error_message=(
            "Failed to deserialize cached event list for key {key}: {error}"
        ),
    )
    async def list_events(
        self,
        *,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[EventListItem]:
        """List events with optional filtering and pagination."""

        events = await self._repository.list_events(
            status=status, limit=limit, offset=offset
        )
        return list(events)

    @cached(
        _event_detail_cache_key,
        ttl=EVENT_DETAIL_TTL_SECONDS,
        serializer=_serialize_event_detail,
        deserializer=_deserialize_event_detail,
        deserialize_error_message=(
            "Failed to deserialize cached event detail for key {key}: {error}"
        ),
    )
    async def get_event(self, event_id: str) -> EventDetail | None:
        """Get detailed event information by ID."""
        return await self._repository.get_event(event_id)

    @cached(
        lambda _self, *, limit=25, offset=0: _event_list_cache_key(
            _self, status="upcoming", limit=limit, offset=offset
        ),
        ttl=EVENT_LIST_TTL_SECONDS,
        serializer=_serialize_event_list,
        deserializer=_deserialize_event_list,
        deserialize_error_message=(
            "Failed to deserialize cached upcoming events for key {key}: {error}"
        ),
    )
    async def list_upcoming_events(
        self, *, limit: int = 25, offset: int = 0
    ) -> list[EventListItem]:
        """List upcoming events using deterministic pagination defaults."""

        return await self.list_events(status="upcoming", limit=limit, offset=offset)

    async def list_completed_events(
        self, *, limit: int | None = None, offset: int | None = None
    ) -> list[EventListItem]:
        """List completed events with pagination."""
        return await self.list_events(status="completed", limit=limit, offset=offset)

    async def get_paginated_events(
        self,
        *,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedEventsResponse:
        """Get paginated events with total count and has_more flag."""
        events = await self.list_events(status=status, limit=limit, offset=offset)
        total = await self._repository.count_events(status=status)
        has_more = (offset + limit) < total

        return PaginatedEventsResponse(
            events=events,
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more,
        )

    async def count_events(self, *, status: str | None = None) -> int:
        """Count total number of events."""
        return await self._repository.count_events(status=status)

    async def search_events(
        self,
        *,
        q: str | None = None,
        year: int | None = None,
        location: str | None = None,
        event_type: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedEventsResponse:
        """Search and filter events with advanced options."""
        events = await self._repository.search_events(
            q=q,
            year=year,
            location=location,
            event_type=event_type,
            status=status,
            limit=limit,
            offset=offset,
        )
        event_list = list(events)

        # Get total count with same filters (but no pagination)
        all_matching = await self._repository.search_events(
            q=q,
            year=year,
            location=location,
            event_type=event_type,
            status=status,
            limit=None,
            offset=None,
        )
        total = len(list(all_matching))
        has_more = (offset + limit) < total

        return PaginatedEventsResponse(
            events=event_list,
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more,
        )

    async def get_filter_options(self) -> tuple[list[int], list[str]]:
        """Get available filter options (years and locations)."""
        years = await self._repository.get_unique_years()
        locations = await self._repository.get_unique_locations()
        return years, locations
