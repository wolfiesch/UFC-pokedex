"""Unit tests covering the caching behaviour of :mod:`backend.services.event_service`."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from backend.schemas.event import EventDetail, EventListItem
from backend.services import caching as caching_utils
from backend.services.event_service import EventService


class FakeCache:
    """Simple in-memory cache double that mimics :class:`backend.cache.CacheClient`."""

    def __init__(self) -> None:
        self.payloads: dict[str, Any] = {}

    async def get_json(self, key: str) -> Any:
        return self.payloads.get(key)

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        self.payloads[key] = value


class StubEventRepository:
    """Repository double that records invocation counts for assertions."""

    def __init__(self) -> None:
        self.list_events_calls = 0
        self.get_event_calls = 0

        self._events = [
            EventListItem(
                event_id="evt-001",
                name="UFC Test Night",
                date=date(2025, 3, 21),
                location="Las Vegas",
                status="upcoming",
                event_type="fight_night",
            ),
            EventListItem(
                event_id="evt-002",
                name="UFC Demo Card",
                date=date(2025, 4, 4),
                location="New York",
                status="upcoming",
                event_type="ppv",
            ),
        ]

    async def list_events(
        self,
        *,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[EventListItem]:
        self.list_events_calls += 1
        return self._events

    async def get_event(self, event_id: str) -> EventDetail | None:
        self.get_event_calls += 1
        if event_id != "evt-001":
            return None
        return EventDetail(
            event_id="evt-001",
            name="UFC Test Night",
            date=date(2025, 3, 21),
            location="Las Vegas",
            status="upcoming",
            event_type="fight_night",
            fight_card=[],
        )


@pytest.mark.asyncio
async def test_list_events_uses_distributed_cache_when_available() -> None:
    """The cache decorator should avoid repository calls when data is cached."""

    caching_utils._local_cache.clear()  # type: ignore[attr-defined]
    repository = StubEventRepository()
    cache = FakeCache()
    service = EventService(repository, cache=cache)

    first_call = await service.list_events(status="upcoming", limit=10, offset=0)
    assert repository.list_events_calls == 1

    second_call = await service.list_events(status="upcoming", limit=10, offset=0)
    assert repository.list_events_calls == 1
    assert second_call == first_call
    assert cache.payloads  # Cache should contain at least one entry
    caching_utils._local_cache.clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_get_event_falls_back_to_in_process_cache_without_client() -> None:
    """Even without Redis the local cache should prevent duplicate repository calls."""

    caching_utils._local_cache.clear()  # type: ignore[attr-defined]
    repository = StubEventRepository()
    service = EventService(repository, cache=None)

    result = await service.get_event("evt-001")
    assert result is not None
    assert repository.get_event_calls == 1

    cached = await service.get_event("evt-001")
    assert repository.get_event_calls == 1
    assert cached == result
    caching_utils._local_cache.clear()  # type: ignore[attr-defined]
