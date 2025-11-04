from fastapi import APIRouter, Depends, HTTPException, Query

from backend.schemas.event import EventDetail, EventListItem, PaginatedEventsResponse
from backend.services.event_service import EventService, get_event_service

router = APIRouter()


@router.get("/", response_model=PaginatedEventsResponse)
async def list_events(
    status: str | None = Query(
        None, description="Filter by status: 'upcoming' or 'completed'"
    ),
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
