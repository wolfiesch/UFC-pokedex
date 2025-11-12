"""Event repository implementation for PostgreSQL-backed storage."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import and_, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import ColumnElement

from backend.db.models import Event, Fighter
from backend.schemas.event import EventDetail, EventFight, EventListItem
from backend.utils.event_utils import detect_event_type


class PostgreSQLEventRepository:
    """Repository for event data using PostgreSQL database."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _build_search_conditions(
        self,
        *,
        q: str | None,
        year: int | None,
        location: str | None,
        status: str | None,
    ) -> list[ColumnElement[bool]]:
        """Create SQLAlchemy filter expressions shared by search queries.

        Each generated predicate mirrors the filtering performed within
        :meth:`search_events` so that both listing and counting paths stay in
        sync. Centralising this logic avoids subtle drift between the two
        code paths as new filters are introduced.
        """

        conditions: list[ColumnElement[bool]] = []

        # Text search in event name and location.
        if q:
            search_pattern = f"%{q}%"
            conditions.append(
                Event.name.ilike(search_pattern) | Event.location.ilike(search_pattern)
            )

        # Year filter applied by extracting the year component from the event date.
        if year:
            conditions.append(func.extract("year", Event.date) == year)

        # Location filter performs case-insensitive partial matching.
        if location:
            conditions.append(Event.location.ilike(f"%{location}%"))

        # Status filter limits results to the desired lifecycle stage.
        if status:
            conditions.append(Event.status == status)

        return conditions

    def _event_type_expression(self) -> ColumnElement[str]:
        """Return SQL expression approximating :func:`detect_event_type`.

        The classification pipeline relies on a series of keyword checks. This
        helper reproduces the same ordering using SQL ``CASE`` statements so
        that event-type aware queries can remain entirely server-side.
        """

        lower_name = func.lower(Event.name)

        return case(
            # Pay-per-view cards: "UFC <number>: ..." style naming.
            (
                and_(
                    lower_name.like("ufc %:%"),
                    func.substr(lower_name, 5, 1).between("0", "9"),
                ),
                "ppv",
            ),
            # Fight Night events explicitly mention the label.
            (lower_name.like("%fight night%"), "fight_night"),
            # ESPN and ABC specials rely on their network designations.
            (
                or_(
                    lower_name.like("%ufc on espn%"),
                    lower_name.like("%espn%"),
                ),
                "ufc_on_espn",
            ),
            (
                or_(
                    lower_name.like("%ufc on abc%"),
                    lower_name.like("%abc%"),
                ),
                "ufc_on_abc",
            ),
            # The Ultimate Fighter finales mention both "tuf" and "finale".
            (
                and_(
                    lower_name.like("%tuf%"),
                    lower_name.like("%finale%"),
                ),
                "tuf_finale",
            ),
            # Contender Series cards sometimes surface as DWCS branded shows.
            (
                or_(
                    lower_name.like("%contender series%"),
                    lower_name.like("%dwcs%"),
                ),
                "contender_series",
            ),
            else_="other",
        )

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

        for condition in self._build_search_conditions(
            q=q, year=year, location=location, status=status
        ):
            query = query.where(condition)

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

    async def count_search_events(
        self,
        *,
        q: str | None = None,
        year: int | None = None,
        location: str | None = None,
        event_type: str | None = None,
        status: str | None = None,
    ) -> int:
        """Count events matching the search filters without materialising rows."""

        event_type_expr = self._event_type_expression().label("computed_event_type")

        typed_events_query = select(
            Event.id.label("event_id"),
            event_type_expr,
        )

        for condition in self._build_search_conditions(
            q=q, year=year, location=location, status=status
        ):
            typed_events_query = typed_events_query.where(condition)

        # The common table expression ensures the event-type label is computed
        # a single time before applying any optional filters.
        typed_events_cte = typed_events_query.cte("typed_events")

        count_query = select(func.count()).select_from(typed_events_cte)
        if event_type:
            count_query = count_query.where(
                typed_events_cte.c.computed_event_type == event_type
            )

        result = await self._session.execute(count_query)
        count = result.scalar_one_or_none()
        return int(count or 0)

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
