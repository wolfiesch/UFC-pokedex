"""Event repository implementation for PostgreSQL-backed storage."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.models import Event, Fighter
from backend.schemas.event import EventDetail, EventFight, EventListItem
from backend.utils.event_utils import detect_event_type


class PostgreSQLEventRepository:
    """Repository for event data using PostgreSQL database."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_events(
        self,
        *,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Iterable[EventListItem]:
        """List all events with optional filtering and pagination."""
        query = select(Event).order_by(desc(Event.date), Event.id)

        # Filter by status if provided
        if status:
            query = query.where(Event.status == status)

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        result = await self._session.execute(query)
        events = result.scalars().all()

        return [
            EventListItem(
                event_id=event.id,
                name=event.name,
                date=event.date,
                location=event.location,
                status=event.status,
                venue=event.venue,
                broadcast=event.broadcast,
                event_type=detect_event_type(event.name).value,
            )
            for event in events
        ]

    async def get_event(self, event_id: str) -> EventDetail | None:
        """Get detailed event information by ID, including fight card."""
        # Query event with fights relationship loaded
        query = (
            select(Event)
            .where(Event.id == event_id)
            .options(selectinload(Event.fights))
        )
        result = await self._session.execute(query)
        event = result.scalar_one_or_none()

        if event is None:
            return None

        # Build fight card from fights linked to this event
        fight_card: list[EventFight] = []

        # Aggregate fighter identifiers to avoid N+1 lookups.
        fighter_ids: set[str] = {
            fight.fighter_id for fight in event.fights if fight.fighter_id
        }
        fighter_ids.update(
            opponent_id
            for opponent_id in (fight.opponent_id for fight in event.fights)
            if opponent_id
        )
        fighter_lookup: dict[str, str] = {}
        if fighter_ids:
            fighter_rows = await self._session.execute(
                select(Fighter.id, Fighter.name).where(Fighter.id.in_(fighter_ids))
            )
            fighter_lookup = {row.id: row.name for row in fighter_rows.all()}

        for fight in event.fights:
            fighter_1_id = fight.fighter_id
            fighter_2_id = fight.opponent_id

            fighter_1_name = fighter_lookup.get(fighter_1_id, "Unknown")

            fighter_2_name = fight.opponent_name
            if fighter_2_id:
                fighter_2_name = fighter_lookup.get(fighter_2_id, fighter_2_name)

            fight_card.append(
                EventFight(
                    fight_id=fight.id,
                    fighter_1_id=fighter_1_id,
                    fighter_1_name=fighter_1_name,
                    fighter_2_id=fighter_2_id,
                    fighter_2_name=fighter_2_name,
                    # Propagate stored weight class for downstream context.
                    weight_class=fight.weight_class,
                    result=fight.result,
                    method=fight.method,
                    round=fight.round,
                    time=fight.time,
                )
            )

        return EventDetail(
            event_id=event.id,
            name=event.name,
            date=event.date,
            location=event.location,
            status=event.status,
            venue=event.venue,
            broadcast=event.broadcast,
            event_type=detect_event_type(event.name).value,
            promotion=event.promotion,
            ufcstats_url=event.ufcstats_url,
            tapology_url=event.tapology_url,
            sherdog_url=event.sherdog_url,
            fight_card=fight_card,
        )

    async def list_upcoming_events(self) -> Iterable[EventListItem]:
        """List only upcoming events."""
        return await self.list_events(status="upcoming")

    async def list_completed_events(
        self, *, limit: int | None = None, offset: int | None = None
    ) -> Iterable[EventListItem]:
        """List only completed events with pagination."""
        return await self.list_events(status="completed", limit=limit, offset=offset)

    async def count_events(self, *, status: str | None = None) -> int:
        """Count total number of events, optionally filtered by status."""
        query = select(func.count()).select_from(Event)
        if status:
            query = query.where(Event.status == status)

        result = await self._session.execute(query)
        count = result.scalar_one_or_none()
        return count if count is not None else 0

    async def search_events(
        self,
        *,
        q: str | None = None,
        year: int | None = None,
        location: str | None = None,
        event_type: str | None = None,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Iterable[EventListItem]:
        """
        Search and filter events.

        Args:
            q: Search query (searches in event name, location)
            year: Filter by year
            location: Filter by location (case-insensitive partial match)
            event_type: Filter by event type (ppv, fight_night, etc.)
            status: Filter by status (upcoming, completed)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching events
        """
        query = select(Event).order_by(desc(Event.date), Event.id)

        # Text search in name and location
        if q:
            search_pattern = f"%{q}%"
            query = query.where(
                Event.name.ilike(search_pattern) | Event.location.ilike(search_pattern)
            )

        # Year filter
        if year:
            query = query.where(func.extract("year", Event.date) == year)

        # Location filter
        if location:
            query = query.where(Event.location.ilike(f"%{location}%"))

        # Status filter
        if status:
            query = query.where(Event.status == status)

        apply_manual_pagination = event_type is not None

        # ``detect_event_type`` performs in-memory classification. When an
        # event_type filter is supplied we must load all matching rows prior to
        # the post-processing step to ensure pagination remains accurate.
        if not apply_manual_pagination:
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)

        result = await self._session.execute(query)
        events = result.scalars().all()

        # Build event list with event type detection
        event_list = [
            EventListItem(
                event_id=event.id,
                name=event.name,
                date=event.date,
                location=event.location,
                status=event.status,
                venue=event.venue,
                broadcast=event.broadcast,
                event_type=detect_event_type(event.name).value,
            )
            for event in events
        ]

        # Filter by event_type after detection (since it's not in DB)
        if event_type:
            event_list = [
                event for event in event_list if event.event_type == event_type
            ]

        if not apply_manual_pagination:
            return event_list

        start_index: int = 0 if offset is None else offset
        end_index: int | None = None if limit is None else start_index + limit
        return event_list[start_index:end_index]

    async def get_unique_years(self) -> list[int]:
        """Get list of unique years from all events."""
        query = select(func.extract("year", Event.date).distinct()).order_by(
            desc(func.extract("year", Event.date))
        )
        result = await self._session.execute(query)
        years = result.scalars().all()
        return [int(year) for year in years if year is not None]

    async def get_unique_locations(self) -> list[str]:
        """Get list of unique locations from all events."""
        query = (
            select(Event.location.distinct())
            .where(Event.location.isnot(None))
            .order_by(Event.location)
        )
        result = await self._session.execute(query)
        locations = result.scalars().all()
        return list(locations)

    async def count_search_events(
        self,
        *,
        q: str | None = None,
        year: int | None = None,
        location: str | None = None,
        event_type: str | None = None,
        status: str | None = None,
    ) -> int:
        """
        Count events matching search criteria.

        Args:
            q: Search query (searches in event name, location)
            year: Filter by year
            location: Filter by location (case-insensitive partial match)
            event_type: Filter by event type (ppv, fight_night, etc.)
            status: Filter by status (upcoming, completed)

        Returns:
            Total count of matching events
        """
        # If event_type is specified, we must do post-processing
        # So we need to fetch all matching events and filter in memory
        if event_type is not None:
            # Fall back to fetching all results and counting
            results = await self.search_events(
                q=q,
                year=year,
                location=location,
                event_type=event_type,
                status=status,
                limit=None,
                offset=None,
            )
            return len(list(results))

        # Build count query with same filters as search_events
        query = select(func.count()).select_from(Event)

        # Text search in name and location
        if q:
            search_pattern = f"%{q}%"
            query = query.where(
                Event.name.ilike(search_pattern) | Event.location.ilike(search_pattern)
            )

        # Year filter
        if year:
            query = query.where(func.extract("year", Event.date) == year)

        # Location filter
        if location:
            query = query.where(Event.location.ilike(f"%{location}%"))

        # Status filter
        if status:
            query = query.where(Event.status == status)

        result = await self._session.execute(query)
        count = result.scalar_one_or_none()
        return count if count is not None else 0

