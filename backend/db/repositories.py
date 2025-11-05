"""Backward compatibility facade for refactored repository layer.

This module maintains the original PostgreSQLFighterRepository and
PostgreSQLEventRepository interfaces while delegating to specialized
repositories internally. This ensures zero breaking changes for existing code.

The monolithic repository has been split into:
- FighterRepository: Fighter CRUD operations
- FightGraphRepository: Fight relationship graphs
- StatsRepository: Analytics and aggregations
- FightRepository: Fight CRUD operations
- PostgreSQLEventRepository: Event operations (unchanged)

All existing code continues to work without modification.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from typing import Literal

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from backend.db.models import Event, Fight, Fighter
from backend.db.repositories.fight_graph_repository import FightGraphRepository
from backend.db.repositories.fight_repository import FightRepository
from backend.db.repositories.fighter_repository import FighterRepository
from backend.db.repositories.stats_repository import StatsRepository
from backend.schemas.event import EventDetail, EventFight, EventListItem
from backend.schemas.fight_graph import FightGraphResponse
from backend.schemas.fighter import (
    FighterComparisonEntry,
    FighterDetail,
    FighterListItem,
)
from backend.schemas.stats import (
    LeaderboardsResponse,
    StatsSummaryResponse,
    TrendsResponse,
)
from backend.utils.event_utils import detect_event_type


class PostgreSQLFighterRepository:
    """Backward compatibility facade delegating to specialized repositories.

    This class maintains the original monolithic interface while internally
    delegating to focused, domain-specific repositories. This ensures existing
    code continues to work without any modifications.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        # Initialize specialized repositories
        self._fighter_repo = FighterRepository(session)
        self._fight_graph_repo = FightGraphRepository(session)
        self._stats_repo = StatsRepository(session)
        self._fight_repo = FightRepository(session)

    # Fighter operations - delegate to FighterRepository
    async def list_fighters(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        include_streak: bool = False,
        streak_window: int = 6,
    ) -> Iterable[FighterListItem]:
        """List all fighters with optional pagination."""
        return await self._fighter_repo.list_fighters(
            limit=limit,
            offset=offset,
            include_streak=include_streak,
            streak_window=streak_window,
        )

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Get detailed fighter information by ID."""
        return await self._fighter_repo.get_fighter(fighter_id)

    async def search_fighters(
        self,
        query: str | None = None,
        stance: str | None = None,
        division: str | None = None,
        champion_statuses: list[str] | None = None,
        streak_type: str | None = None,
        min_streak_count: int | None = None,
        include_streak: bool = False,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[list[FighterListItem], int]:
        """Search fighters by various criteria."""
        return await self._fighter_repo.search_fighters(
            query=query,
            stance=stance,
            division=division,
            champion_statuses=champion_statuses,
            streak_type=streak_type,
            min_streak_count=min_streak_count,
            include_streak=include_streak,
            limit=limit,
            offset=offset,
        )

    async def get_fighters_for_comparison(
        self, fighter_ids: Sequence[str]
    ) -> list[FighterComparisonEntry]:
        """Return stats snapshots for the requested fighters."""
        return await self._fighter_repo.get_fighters_for_comparison(fighter_ids)

    async def count_fighters(self) -> int:
        """Get the total count of fighters."""
        return await self._fighter_repo.count_fighters()

    async def get_random_fighter(self) -> FighterListItem | None:
        """Get a random fighter."""
        return await self._fighter_repo.get_random_fighter()

    async def create_fighter(self, fighter: Fighter) -> Fighter:
        """Create a new fighter."""
        return await self._fighter_repo.create_fighter(fighter)

    async def upsert_fighter(self, fighter_data: dict) -> Fighter:
        """Insert or update a fighter."""
        return await self._fighter_repo.upsert_fighter(fighter_data)

    # Fight graph operations - delegate to FightGraphRepository
    async def get_fight_graph(
        self,
        *,
        division: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 200,
        include_upcoming: bool = False,
    ) -> FightGraphResponse:
        """Aggregate fighters and bout links for visualization."""
        return await self._fight_graph_repo.get_fight_graph(
            division=division,
            start_year=start_year,
            end_year=end_year,
            limit=limit,
            include_upcoming=include_upcoming,
        )

    # Stats operations - delegate to StatsRepository
    async def stats_summary(self) -> StatsSummaryResponse:
        """Get aggregate statistics about fighters."""
        return await self._stats_repo.stats_summary()

    async def get_leaderboards(
        self,
        *,
        limit: int,
        accuracy_metric: str,
        submissions_metric: str,
        start_date: date | None,
        end_date: date | None,
    ) -> LeaderboardsResponse:
        """Compute leaderboard slices."""
        return await self._stats_repo.get_leaderboards(
            limit=limit,
            accuracy_metric=accuracy_metric,
            submissions_metric=submissions_metric,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_trends(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        time_bucket: Literal["month", "quarter", "year"],
        streak_limit: int,
    ) -> TrendsResponse:
        """Aggregate longitudinal trends."""
        return await self._stats_repo.get_trends(
            start_date=start_date,
            end_date=end_date,
            time_bucket=time_bucket,
            streak_limit=streak_limit,
        )

    # Fight operations - delegate to FightRepository
    async def create_fight(self, fight: Fight) -> Fight:
        """Create a new fight record."""
        return await self._fight_repo.create_fight(fight)


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

        # Aggregate all fighter identifiers across the card so we can resolve
        # roster metadata in a single round-trip instead of the previous
        # per-fight N+1 query pattern.
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
                    # Propagate the stored weight class so consumers can surface
                    # the division context (e.g., "Lightweight") without extra joins.
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

        # ``detect_event_type`` performs in-memory classification.  When a
        # caller supplies an ``event_type`` filter we must load every matching
        # row first, otherwise the database-level LIMIT/OFFSET could trim
        # relevant events before the post-processing step runs.

        # Pagination
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
        # ``end_index`` remains ``None`` when no limit is supplied so Python's
        # slice semantics naturally return the full remainder of the sequence.
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
