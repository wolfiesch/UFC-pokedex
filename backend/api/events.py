from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.schemas.event import EventDetail, EventListItem, PaginatedEventsResponse
from backend.services.event_service import EventService, get_event_service

router = APIRouter()


class EventFilterOptions(BaseModel):
    """Available filter options for events."""

    years: list[int]
    locations: list[str]
    event_types: list[str]


@router.get("", response_model=PaginatedEventsResponse)
@router.get("/", response_model=PaginatedEventsResponse)
async def list_events(
    status: str | None = Query(None, description="Filter by status: 'upcoming' or 'completed'"),
    limit: int = Query(20, ge=1, le=100, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    service: EventService = Depends(get_event_service),
) -> PaginatedEventsResponse:
    """List events with optional filtering and pagination."""
    return await service.get_paginated_events(status=status, limit=limit, offset=offset)


@router.get("/upcoming", response_model=list[EventListItem])
async def list_upcoming_events(
    service: EventService = Depends(get_event_service),
) -> list[EventListItem]:
    """List all upcoming UFC events."""
    return await service.list_upcoming_events()


@router.get("/completed", response_model=PaginatedEventsResponse)
async def list_completed_events(
    limit: int = Query(20, ge=1, le=100, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    service: EventService = Depends(get_event_service),
) -> PaginatedEventsResponse:
    """List completed UFC events with pagination."""
    return await service.get_paginated_events(status="completed", limit=limit, offset=offset)


@router.get("/search/", response_model=PaginatedEventsResponse)
async def search_events(
    q: str | None = Query(None, description="Search query for event name or location"),
    year: int | None = Query(None, description="Filter by year"),
    location: str | None = Query(None, description="Filter by location"),
    event_type: str | None = Query(
        None, description="Filter by event type (ppv, fight_night, etc.)"
    ),
    status: str | None = Query(None, description="Filter by status (upcoming, completed)"),
    limit: int = Query(20, ge=1, le=100, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    service: EventService = Depends(get_event_service),
) -> PaginatedEventsResponse:
    """Search and filter events with advanced options."""
    return await service.search_events(
        q=q,
        year=year,
        location=location,
        event_type=event_type,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/filters/options", response_model=EventFilterOptions)
async def get_filter_options(
    service: EventService = Depends(get_event_service),
) -> EventFilterOptions:
    """Get available filter options (unique years, locations, event types)."""
    years, locations = await service.get_filter_options()
    return EventFilterOptions(
        years=years,
        locations=locations,
        event_types=[
            "ppv",
            "fight_night",
            "ufc_on_espn",
            "ufc_on_abc",
            "tuf_finale",
            "contender_series",
            "other",
        ],
    )


@router.get("/{event_id}", response_model=EventDetail)
async def get_event(
    event_id: str,
    service: EventService = Depends(get_event_service),
) -> EventDetail:
    """Get detailed information about a specific event, including fight card."""
    event = await service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
