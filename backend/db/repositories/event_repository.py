"""Event repository implementation for PostgreSQL-backed storage."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

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

    def _build_search_events_query(
        self,
        *,
        q: str | None = None,
        year: int | None = None,
        location: str | None = None,
        status: str | None = None,
    ) -> Select[tuple[Event]]:
        """Construct the reusable ``SELECT`` statement for event searches.

        The repository executes this helper twice per request: once to fetch the
        actual ``Event`` rows (optionally with pagination) and once wrapped as a
        subquery to compute ``COUNT(*)``. Centralizing the base filters prevents
        drift between the data and the pagination metadata, ensuring the total
        reported to clients always mirrors the applied constraints.
        """

        query: Select[tuple[Event]] = select(Event).order_by(desc(Event.date), Event.id)

        if q:
            search_pattern = f"%{q}%"
            query = query.where(
                Event.name.ilike(search_pattern) | Event.location.ilike(search_pattern)
            )

        if year:
            query = query.where(func.extract("year", Event.date) == year)

        if location:
            query = query.where(Event.location.ilike(f"%{location}%"))

        if status:
            query = query.where(Event.status == status)

        return query

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
    ) -> tuple[list[EventListItem], int]:
        """Search and filter events, returning both the page and total count."""

        base_query: Select[tuple[Event]] = self._build_search_events_query(
            q=q,
            year=year,
            location=location,
            status=status,
        )

        # Execute the database-level count using the shared filter set so the
        # pagination metadata mirrors the page contents.
        count_query: Select[tuple[int]] = select(func.count()).select_from(
            base_query.order_by(None).subquery()
        )
        count_result = await self._session.execute(count_query)
        total_from_database = count_result.scalar_one_or_none() or 0
        total_count: int = int(total_from_database)

        apply_manual_pagination = event_type is not None
        rows_query: Select[tuple[Event]] = base_query
        if not apply_manual_pagination:
            if offset is not None:
                rows_query = rows_query.offset(offset)
            if limit is not None:
                rows_query = rows_query.limit(limit)

        result = await self._session.execute(rows_query)
        events = result.scalars().all()

        event_items: list[EventListItem] = [
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

        filtered_items: list[EventListItem]
        if event_type is not None:
            filtered_items = [
                item for item in event_items if item.event_type == event_type
            ]
        else:
            filtered_items = event_items

        if apply_manual_pagination:
            # ``detect_event_type`` is computed in Python, so totals must be
            # derived from the filtered collection instead of the SQL count.
            total_count = len(filtered_items)
            start_index: int = 0 if offset is None else offset
            end_index: int | None = None if limit is None else start_index + limit
            page_items: list[EventListItem] = filtered_items[start_index:end_index]
        else:
            page_items = filtered_items

        return page_items, total_count

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
