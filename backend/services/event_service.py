from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import CacheClient, get_cache_client
from backend.db.connection import get_db
from backend.db.repositories import PostgreSQLEventRepository
from backend.schemas.event import EventDetail, EventListItem, PaginatedEventsResponse

logger = logging.getLogger(__name__)


class EventService:
    """Service layer for event operations with optional caching."""

    def __init__(
        self,
        repository: PostgreSQLEventRepository,
        cache: CacheClient | None = None,
    ) -> None:
        self._repository = repository
        self._cache = cache

    async def _cache_get(self, key: str) -> Any:
        if self._cache is None:
            return None
        return await self._cache.get_json(key)

    async def _cache_set(self, key: str, value: Any, ttl: int | None = None) -> None:
        if self._cache is None:
            return
        await self._cache.set_json(key, value, ttl=ttl)

    async def list_events(
        self,
        *,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[EventListItem]:
        """List events with optional filtering and pagination."""
        # Create cache key
        use_cache = (
            self._cache is not None
            and limit is not None
            and offset is not None
            and limit >= 0
            and offset >= 0
        )
        cache_key = (
            f"events:list:status={status or 'all'}:limit={limit}:offset={offset}"
            if use_cache
            else None
        )

        # Try cache first
        if use_cache and cache_key is not None:
            cached = await self._cache_get(cache_key)
            if isinstance(cached, list):
                try:
                    return [EventListItem.model_validate(item) for item in cached]
                except ValidationError as exc:
                    logger.warning(
                        "Failed to deserialize cached event list for key %s: %s",
                        cache_key,
                        exc,
                    )

        # Fetch from repository
        events = await self._repository.list_events(
            status=status, limit=limit, offset=offset
        )
        event_list = list(events)

        # Cache result
        if use_cache and cache_key is not None:
            await self._cache_set(
                cache_key,
                [event.model_dump() for event in event_list],
                ttl=300,  # 5 minutes
            )

        return event_list

    async def get_event(self, event_id: str) -> EventDetail | None:
        """Get detailed event information by ID."""
        cache_key = f"events:detail:{event_id}"
        cached = await self._cache_get(cache_key)
        if isinstance(cached, dict):
            try:
                return EventDetail.model_validate(cached)
            except ValidationError as exc:
                logger.warning(
                    "Failed to deserialize cached event detail for key %s: %s",
                    cache_key,
                    exc,
                )

        event = await self._repository.get_event(event_id)
        if event:
            await self._cache_set(cache_key, event.model_dump(), ttl=600)  # 10 minutes
        return event

    async def list_upcoming_events(self) -> list[EventListItem]:
        """List all upcoming events."""
        return await self.list_events(status="upcoming")

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

        # Get total count with same filters using optimized count query
        total = await self._repository.count_search_events(
            q=q,
            year=year,
            location=location,
            event_type=event_type,
            status=status,
        )
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


async def get_event_service(
    session: AsyncSession = Depends(get_db),
    cache: CacheClient = Depends(get_cache_client),
) -> EventService:
    """FastAPI dependency that wires the event repository and cache layer."""
    repository = PostgreSQLEventRepository(session)
    return EventService(repository, cache=cache)
