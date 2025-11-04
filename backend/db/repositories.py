from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import Float, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.models import Event, Fight, Fighter, fighter_stats
from backend.schemas.event import EventDetail, EventFight, EventListItem
from backend.schemas.fight_graph import (
    FightGraphLink,
    FightGraphNode,
    FightGraphResponse,
)
from backend.schemas.fighter import (
    FighterComparisonEntry,
    FighterDetail,
    FighterListItem,
    FightHistoryEntry,
)
from backend.schemas.stats import (
    AverageFightDuration,
    LeaderboardDefinition,
    LeaderboardEntry,
    LeaderboardsResponse,
    StatsSummaryMetric,
    StatsSummaryResponse,
    TrendPoint,
    TrendSeries,
    TrendsResponse,
    WinStreakSummary,
)
from backend.services.image_resolver import resolve_fighter_image


def _invert_fight_result(result: str | None) -> str:
    """Invert a fight result from one fighter's perspective to the opponent's.

    Examples:
        'win' -> 'loss'
        'loss' -> 'win'
        'W' -> 'L'
        'draw' -> 'draw'
        'NC' -> 'NC'
    """
    if not result:
        return "Unknown"

    result_lower = result.lower().strip()

    # Handle common result formats
    if result_lower in ("w", "win"):
        return "loss"
    elif result_lower in ("l", "loss"):
        return "win"
    elif result_lower in ("d", "draw", "draw-majority", "draw-split"):
        return result  # Draws stay the same
    elif result_lower in ("nc", "no contest"):
        return result  # No contests stay the same
    elif result_lower == "next":
        return result  # Upcoming fights stay the same
    else:
        # Unknown result format, return as-is
        return result


def _normalize_result_category(result: str | None) -> str:
    """Normalize varying result strings into shared categories for analytics."""

    if result is None:
        return "other"

    normalized_result = result.strip().lower()
    if normalized_result in {"win", "w"}:
        return "win"
    if normalized_result in {"loss", "l"}:
        return "loss"
    if normalized_result.startswith("draw"):
        return "draw"
    if normalized_result in {"nc", "no contest"}:
        return "nc"
    if normalized_result == "next":
        return "upcoming"
    return "other"


def _empty_breakdown() -> dict[str, int]:
    """Return a pre-seeded result breakdown dictionary."""

    return {
        "win": 0,
        "loss": 0,
        "draw": 0,
        "nc": 0,
        "upcoming": 0,
        "other": 0,
    }


def _calculate_age(*, dob: date | None, reference_date: date) -> int | None:
    """Return the fighter's age in whole years relative to ``reference_date``.

    The repository persists birth dates as naive ``date`` objects.  To produce a
    consistent age value regardless of timezone or repeated invocations within a
    single request, the caller supplies a ``reference_date`` (typically the
    cached "today" value).  When a birth date is missing, the schema expects the
    age field to be ``None`` so API consumers can distinguish between unknown
    data and a legitimate age of zero.

    Args:
        dob: The fighter's date of birth, or ``None`` when the value is
            unavailable in the source dataset.
        reference_date: The "current" date used for the calculation.  Tests
            provide a deterministic value to keep expectations stable, while
            production calls use a timezone-aware UTC date snapshot.

    Returns:
        The integer age when ``dob`` is present.  ``None`` is returned for
        missing data, and ages are never negative—future-dated birthdays are
        clamped to zero so downstream code does not encounter surprising
        negative integers.
    """

    if dob is None:
        return None

    if dob > reference_date:
        # Guard against bad data entering the system by never returning a
        # negative age.  The value will be zero until the reference date moves
        # beyond the erroneous future birthday.
        return 0

    years_elapsed: int = reference_date.year - dob.year
    has_had_birthday: bool = (reference_date.month, reference_date.day) >= (
        dob.month,
        dob.day,
    )
    return years_elapsed if has_had_birthday else years_elapsed - 1


class PostgreSQLFighterRepository:
    """Repository for fighter data using PostgreSQL database."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_fighters(
        self, *, limit: int | None = None, offset: int | None = None
    ) -> Iterable[FighterListItem]:
        """List all fighters with optional pagination."""
        query = select(Fighter).order_by(Fighter.name, Fighter.id)

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        result = await self._session.execute(query)
        fighters = result.scalars().all()

        return [
            FighterListItem(
                fighter_id=fighter.id,
                detail_url=f"http://www.ufcstats.com/fighter-details/{fighter.id}",
                name=fighter.name,
                nickname=fighter.nickname,
                record=fighter.record,
                division=fighter.division,
                height=fighter.height,
                weight=fighter.weight,
                reach=fighter.reach,
                stance=fighter.stance,
                dob=fighter.dob,
                image_url=resolve_fighter_image(fighter.id, fighter.image_url),
            )
            for fighter in fighters
        ]

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Get detailed fighter information by ID."""
        # Query fighter details
        fighter_query = select(Fighter).where(Fighter.id == fighter_id)
        fighter_result = await self._session.execute(fighter_query)
        fighter = fighter_result.scalar_one_or_none()

        if fighter is None:
            return None

        # Query fighter stats
        stats_result = await self._session.execute(
            select(
                fighter_stats.c.category,
                fighter_stats.c.metric,
                fighter_stats.c.value,
            ).where(fighter_stats.c.fighter_id == fighter_id)
        )
        stats_map: dict[str, dict[str, str]] = {}
        for category, metric, value in stats_result.all():
            if category is None or metric is None:
                continue
            category_stats = stats_map.setdefault(category, {})
            category_stats[metric] = value

        # Query fights from BOTH perspectives:
        # 1. Fights where this fighter is fighter_id
        # 2. Fights where this fighter is opponent_id
        fights_query = select(Fight).where(
            (Fight.fighter_id == fighter_id) | (Fight.opponent_id == fighter_id)
        )
        fights_result = await self._session.execute(fights_query)
        all_fights = fights_result.scalars().all()

        # Build fight history, inverting perspective when needed
        fight_history: list[FightHistoryEntry] = []
        for fight in all_fights:
            if fight.fighter_id == fighter_id:
                # Fight is from this fighter's perspective - use as-is
                fight_history.append(
                    FightHistoryEntry(
                        fight_id=fight.id,
                        event_name=fight.event_name,
                        event_date=fight.event_date,
                        opponent=fight.opponent_name,
                        opponent_id=fight.opponent_id,
                        result=fight.result,
                        method=fight.method or "",
                        round=fight.round,
                        time=fight.time,
                        fight_card_url=fight.fight_card_url,
                        stats={},  # TODO: Add fight stats if available
                    )
                )
            else:
                # Fight is from opponent's perspective - need to invert
                # Get the actual opponent's name (the fighter who has this fight record)
                opponent_query = select(Fighter).where(Fighter.id == fight.fighter_id)
                opponent_result = await self._session.execute(opponent_query)
                opponent_fighter = opponent_result.scalar_one_or_none()

                opponent_name = opponent_fighter.name if opponent_fighter else "Unknown"

                # Invert the result
                inverted_result = _invert_fight_result(fight.result)

                fight_history.append(
                    FightHistoryEntry(
                        fight_id=fight.id,
                        event_name=fight.event_name,
                        event_date=fight.event_date,
                        opponent=opponent_name,
                        opponent_id=fight.fighter_id,  # The original fighter_id is now the opponent
                        result=inverted_result,
                        method=fight.method or "",
                        round=fight.round,
                        time=fight.time,
                        fight_card_url=fight.fight_card_url,
                        stats={},  # TODO: Add fight stats if available
                    )
                )

        # Sort fight history: upcoming fights first, then past fights by most recent
        fight_history.sort(
            key=lambda fight: (
                # Primary: upcoming fights first (result="next" → 0, others → 1)
                0 if fight.result == "next" else 1,
                # Secondary: most recent first (use min date for nulls to push them last)
                -(fight.event_date or date.min).toordinal(),
            )
        )

        today_utc: date = datetime.now(tz=UTC).date()
        fighter_age: int | None = _calculate_age(
            dob=fighter.dob,
            reference_date=today_utc,
        )

        return FighterDetail(
            fighter_id=fighter.id,
            detail_url=f"http://www.ufcstats.com/fighter-details/{fighter.id}",
            name=fighter.name,
            nickname=fighter.nickname,
            height=fighter.height,
            weight=fighter.weight,
            reach=fighter.reach,
            stance=fighter.stance,
            dob=fighter.dob,
            image_url=resolve_fighter_image(fighter.id, fighter.image_url),
            record=fighter.record,
            leg_reach=fighter.leg_reach,
            division=fighter.division,
            age=fighter_age,
            striking=stats_map.get("striking", {}),
            grappling=stats_map.get("grappling", {}),
            significant_strikes=stats_map.get("significant_strikes", {}),
            takedown_stats=stats_map.get("takedown_stats", {}),
            career=stats_map.get("career", {}),
            fight_history=fight_history,
        )

    async def get_fight_graph(
        self,
        *,
        division: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 200,
        include_upcoming: bool = False,
    ) -> FightGraphResponse:
        """Aggregate fighters and bout links suitable for force-directed visualization."""

        if limit is not None and limit <= 0:
            return FightGraphResponse()

        fight_filters: list[Any] = []
        if start_year is not None:
            fight_filters.append(Fight.event_date >= date(start_year, 1, 1))
        if end_year is not None:
            fight_filters.append(Fight.event_date <= date(end_year, 12, 31))
        if not include_upcoming:
            fight_filters.append(func.lower(Fight.result) != "next")

        fight_count_expr = func.count().label("fight_count")
        latest_event_expr = func.max(Fight.event_date).label("latest_event_date")

        fight_counts_query = select(
            Fight.fighter_id, fight_count_expr, latest_event_expr
        ).join(Fighter, Fighter.id == Fight.fighter_id)
        if fight_filters:
            fight_counts_query = fight_counts_query.where(*fight_filters)
        if division:
            fight_counts_query = fight_counts_query.where(Fighter.division == division)
        fight_counts_query = fight_counts_query.group_by(Fight.fighter_id)
        fight_counts_query = fight_counts_query.order_by(desc(fight_count_expr))
        if limit is not None:
            fight_counts_query = fight_counts_query.limit(limit)

        fight_counts_result = await self._session.execute(fight_counts_query)
        fight_counts = fight_counts_result.all()

        id_order = [row.fighter_id for row in fight_counts]
        count_map = {row.fighter_id: int(row.fight_count or 0) for row in fight_counts}
        latest_map = {row.fighter_id: row.latest_event_date for row in fight_counts}

        if not id_order:
            fallback_query = select(Fighter).order_by(Fighter.name, Fighter.id)
            if division:
                fallback_query = fallback_query.where(Fighter.division == division)
            if limit is not None:
                fallback_query = fallback_query.limit(limit)
            fallback_result = await self._session.execute(fallback_query)
            fallback_fighters = fallback_result.scalars().all()
            nodes = [
                FightGraphNode(
                    fighter_id=fighter.id,
                    name=fighter.name,
                    division=fighter.division,
                    record=fighter.record,
                    image_url=resolve_fighter_image(fighter.id, fighter.image_url),
                    total_fights=0,
                    latest_event_date=None,
                )
                for fighter in fallback_fighters
            ]
            metadata = {
                "filters": {
                    "division": division,
                    "start_year": start_year,
                    "end_year": end_year,
                    "include_upcoming": include_upcoming,
                },
                "node_count": len(nodes),
                "link_count": 0,
                "limit": limit,
            }
            return FightGraphResponse(nodes=nodes, links=[], metadata=metadata)

        fighters_query = select(Fighter).where(Fighter.id.in_(id_order))
        fighters_result = await self._session.execute(fighters_query)
        fighters = fighters_result.scalars().all()
        fighter_map = {fighter.id: fighter for fighter in fighters}

        nodes: list[FightGraphNode] = []
        for fighter_id in id_order:
            fighter = fighter_map.get(fighter_id)
            if fighter is None:
                continue
            nodes.append(
                FightGraphNode(
                    fighter_id=fighter.id,
                    name=fighter.name,
                    division=fighter.division,
                    record=fighter.record,
                    image_url=resolve_fighter_image(fighter.id, fighter.image_url),
                    total_fights=count_map.get(fighter.id, 0),
                    latest_event_date=latest_map.get(fighter.id),
                )
            )

        id_set = set(id_order)
        edges_filters = list(fight_filters)

        edges_query = select(Fight).where(
            Fight.fighter_id.in_(id_set),
            Fight.opponent_id.is_not(None),
            Fight.opponent_id.in_(id_set),
        )
        if edges_filters:
            edges_query = edges_query.where(*edges_filters)

        edges_result = await self._session.execute(edges_query)
        fights = edges_result.scalars().all()

        link_accumulator: dict[tuple[str, str], dict[str, Any]] = {}
        earliest_event: date | None = None
        latest_event: date | None = None
        for fight in fights:
            opponent_id = fight.opponent_id
            if opponent_id is None:
                continue

            pair = tuple(sorted((fight.fighter_id, opponent_id)))
            if pair[0] == pair[1]:
                continue

            entry = link_accumulator.setdefault(
                pair,
                {
                    "fights": 0,
                    "first_event_name": None,
                    "first_event_date": None,
                    "last_event_name": None,
                    "last_event_date": None,
                    "result_breakdown": {
                        pair[0]: _empty_breakdown(),
                        pair[1]: _empty_breakdown(),
                    },
                },
            )

            entry["fights"] += 1

            result_map = entry["result_breakdown"]
            if fight.fighter_id not in result_map:
                result_map[fight.fighter_id] = _empty_breakdown()

            normalized_result = _normalize_result_category(fight.result)
            if normalized_result not in result_map[fight.fighter_id]:
                result_map[fight.fighter_id][normalized_result] = 0
            result_map[fight.fighter_id][normalized_result] += 1

            other_id = pair[0] if fight.fighter_id == pair[1] else pair[1]
            if other_id not in result_map:
                result_map[other_id] = _empty_breakdown()

            if fight.event_date is not None:
                if earliest_event is None or fight.event_date < earliest_event:
                    earliest_event = fight.event_date
                if latest_event is None or fight.event_date > latest_event:
                    latest_event = fight.event_date

                last_date = entry["last_event_date"]
                if last_date is None or fight.event_date > last_date:
                    entry["last_event_date"] = fight.event_date
                    entry["last_event_name"] = fight.event_name
                first_date = entry["first_event_date"]
                if first_date is None or fight.event_date < first_date:
                    entry["first_event_date"] = fight.event_date
                    entry["first_event_name"] = fight.event_name
            elif entry["last_event_name"] is None:
                entry["last_event_name"] = fight.event_name
                if entry["first_event_name"] is None:
                    entry["first_event_name"] = fight.event_name

        links = [
            FightGraphLink(
                source=pair[0],
                target=pair[1],
                fights=data["fights"],
                first_event_name=data["first_event_name"],
                first_event_date=data["first_event_date"],
                last_event_name=data["last_event_name"],
                last_event_date=data["last_event_date"],
                result_breakdown=data["result_breakdown"],
            )
            for pair, data in link_accumulator.items()
        ]
        links.sort(key=lambda link: link.fights, reverse=True)

        metadata = {
            "filters": {
                "division": division,
                "start_year": start_year,
                "end_year": end_year,
                "include_upcoming": include_upcoming,
            },
            "node_count": len(nodes),
            "link_count": len(links),
            "limit": limit,
        }

        if earliest_event is not None or latest_event is not None:
            metadata["event_window"] = {
                "start": earliest_event,
                "end": latest_event,
            }

        return FightGraphResponse(nodes=nodes, links=links, metadata=metadata)

    async def stats_summary(self) -> StatsSummaryResponse:
        """Get aggregate statistics about fighters."""
        # Count total fighters
        count_query = select(func.count(Fighter.id))
        result = await self._session.execute(count_query)
        total_fighters = result.scalar() or 0

        metrics: list[StatsSummaryMetric] = [
            StatsSummaryMetric(
                id="fighters_indexed",
                label="Fighters Indexed",
                value=float(total_fighters),
                description="Total number of UFC fighters ingested from UFCStats.",
            )
        ]

        avg_sig_accuracy = await self._average_metric("sig_strikes_accuracy_pct")
        if avg_sig_accuracy is not None:
            metrics.append(
                StatsSummaryMetric(
                    id="avg_sig_strikes_accuracy_pct",
                    label="Avg. Sig. Strike Accuracy",
                    value=round(avg_sig_accuracy, 1),
                    description="Average significant strike accuracy across the roster (%).",
                )
            )

        avg_takedown_accuracy = await self._average_metric("takedown_accuracy_pct")
        if avg_takedown_accuracy is not None:
            metrics.append(
                StatsSummaryMetric(
                    id="avg_takedown_accuracy_pct",
                    label="Avg. Takedown Accuracy",
                    value=round(avg_takedown_accuracy, 1),
                    description="Average takedown accuracy rate across all fighters (%).",
                )
            )

        avg_submissions = await self._average_metric("avg_submissions")
        if avg_submissions is not None:
            metrics.append(
                StatsSummaryMetric(
                    id="avg_submission_attempts",
                    label="Avg. Submission Attempts",
                    value=round(avg_submissions, 2),
                    description="Average submission attempts per fight recorded for the roster.",
                )
            )

        avg_fight_duration_seconds = await self._average_metric(
            "avg_fight_duration_seconds"
        )
        if avg_fight_duration_seconds is not None:
            metrics.append(
                StatsSummaryMetric(
                    id="avg_fight_duration_minutes",
                    label="Avg. Fight Duration",
                    value=round(avg_fight_duration_seconds / 60, 1),
                    description="Average fight duration (minutes) derived from recorded bouts.",
                )
            )

        return StatsSummaryResponse(metrics=metrics)

    async def create_fighter(self, fighter: Fighter) -> Fighter:
        """Create a new fighter in the database."""
        self._session.add(fighter)
        await self._session.flush()
        return fighter

    async def upsert_fighter(self, fighter_data: dict) -> Fighter:
        """Insert or update a fighter based on ID."""
        fighter_id = fighter_data.get("id")

        # Check if fighter exists
        query = select(Fighter).where(Fighter.id == fighter_id)
        result = await self._session.execute(query)
        existing_fighter = result.scalar_one_or_none()

        if existing_fighter:
            # Update existing fighter
            for key, value in fighter_data.items():
                if hasattr(existing_fighter, key):
                    setattr(existing_fighter, key, value)
            await self._session.flush()
            return existing_fighter
        else:
            # Create new fighter
            fighter = Fighter(**fighter_data)
            self._session.add(fighter)
            await self._session.flush()
            return fighter

    async def create_fight(self, fight: Fight) -> Fight:
        """Create a new fight record in the database."""
        self._session.add(fight)
        await self._session.flush()
        return fight

    async def search_fighters(
        self,
        query: str | None = None,
        stance: str | None = None,
        division: str | None = None,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[list[FighterListItem], int]:
        """Search fighters by name, stance, or division with pagination support."""

        filters = []
        if query:
            # Use func.lower().like() for database-agnostic case-insensitive search
            # Works with both PostgreSQL and SQLite
            pattern = f"%{query.lower()}%"
            filters.append(
                (func.lower(Fighter.name).like(pattern))
                | (func.lower(Fighter.nickname).like(pattern))
            )
        if stance:
            filters.append(Fighter.stance == stance)
        if division:
            filters.append(Fighter.division == division)

        stmt = select(Fighter).order_by(Fighter.name)
        count_stmt = select(func.count()).select_from(Fighter)

        for condition in filters:
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        if offset is not None and offset > 0:
            stmt = stmt.offset(offset)
        if limit is not None and limit > 0:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        fighters = result.scalars().all()

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        return (
            [
                FighterListItem(
                    fighter_id=fighter.id,
                    detail_url=f"http://www.ufcstats.com/fighter-details/{fighter.id}",
                    name=fighter.name,
                    nickname=fighter.nickname,
                    record=fighter.record,
                    division=fighter.division,
                    height=fighter.height,
                    weight=fighter.weight,
                    reach=fighter.reach,
                    stance=fighter.stance,
                    dob=fighter.dob,
                    image_url=resolve_fighter_image(fighter.id, fighter.image_url),
                )
                for fighter in fighters
            ],
            total,
        )

    async def get_fighters_for_comparison(
        self, fighter_ids: Sequence[str]
    ) -> list[FighterComparisonEntry]:
        """Return stats snapshots for the requested fighters in the input order."""

        if not fighter_ids:
            return []

        ordered_ids: list[str] = []
        for fighter_id in fighter_ids:
            if fighter_id not in ordered_ids:
                ordered_ids.append(fighter_id)

        fighters_stmt = select(Fighter).where(Fighter.id.in_(ordered_ids))
        fighters_result = await self._session.execute(fighters_stmt)
        fighters = fighters_result.scalars().all()
        fighter_map = {fighter.id: fighter for fighter in fighters}

        stats_stmt = (
            select(
                fighter_stats.c.fighter_id,
                fighter_stats.c.category,
                fighter_stats.c.metric,
                fighter_stats.c.value,
            )
            .where(fighter_stats.c.fighter_id.in_(ordered_ids))
            .order_by(fighter_stats.c.fighter_id)
        )

        stats_result = await self._session.execute(stats_stmt)
        stats_by_fighter: dict[str, dict[str, dict[str, str]]] = {}
        for fighter_id, category, metric, value in stats_result.all():
            if fighter_id is None or metric is None or value is None:
                continue
            category_bucket = stats_by_fighter.setdefault(fighter_id, {})
            metric_bucket = category_bucket.setdefault(category or "misc", {})
            metric_bucket[metric] = value

        comparison: list[FighterComparisonEntry] = []
        for fighter_id in ordered_ids:
            fighter = fighter_map.get(fighter_id)
            if fighter is None:
                continue
            # Resolve and cache the fighter's image path even though the
            # comparison payload does not surface the value. The cache keeps
            # subsequent list/detail calls within the same request cycle from
            # repeatedly hitting the filesystem when we are running on SQLite
            # with sparse ``image_url`` columns.
            resolve_fighter_image(fighter_id, fighter.image_url)
            stats_map = stats_by_fighter.get(fighter_id, {})
            comparison.append(
                FighterComparisonEntry(
                    fighter_id=fighter_id,
                    name=fighter.name,
                    record=fighter.record,
                    division=fighter.division,
                    striking=stats_map.get("striking", {}),
                    grappling=stats_map.get("grappling", {}),
                    significant_strikes=stats_map.get("significant_strikes", {}),
                    takedown_stats=stats_map.get("takedown_stats", {}),
                    career=stats_map.get("career", {}),
                )
            )

        return comparison

    async def count_fighters(self) -> int:
        """Get the total count of fighters in the database."""
        query = select(func.count()).select_from(Fighter)
        result = await self._session.execute(query)
        return result.scalar_one()

    async def get_leaderboards(
        self,
        *,
        limit: int,
        accuracy_metric: str,
        submissions_metric: str,
        start_date: date | None,
        end_date: date | None,
    ) -> LeaderboardsResponse:
        """Compute leaderboard slices for accuracy and submission metrics using SQL casts."""

        eligible_fighters = await self._fighters_active_between(start_date, end_date)

        accuracy_entries = await self._collect_leaderboard_entries(
            metric_name=accuracy_metric,
            eligible_fighters=eligible_fighters,
            limit=limit,
        )
        submissions_entries = await self._collect_leaderboard_entries(
            metric_name=submissions_metric,
            eligible_fighters=eligible_fighters,
            limit=limit,
        )

        leaderboards = []

        if accuracy_entries:
            leaderboards.append(
                LeaderboardDefinition(
                    metric_id=accuracy_metric,
                    title="Striking Accuracy",
                    description="Fighters with the highest significant strike accuracy",
                    entries=accuracy_entries,
                )
            )

        if submissions_entries:
            leaderboards.append(
                LeaderboardDefinition(
                    metric_id=submissions_metric,
                    title="Submissions",
                    description="Fighters with the most submission attempts per fight",
                    entries=submissions_entries,
                )
            )

        return LeaderboardsResponse(leaderboards=leaderboards)

    async def get_trends(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        time_bucket: str,
        streak_limit: int,
    ) -> TrendsResponse:
        """Aggregate longitudinal trends such as win streaks and average fight durations."""

        streaks = await self._calculate_win_streaks(
            start_date=start_date, end_date=end_date, limit=streak_limit
        )
        average_durations = await self._calculate_average_durations(
            start_date=start_date, end_date=end_date, time_bucket=time_bucket
        )

        trends: list[TrendSeries] = []

        # Transform win streaks into TrendSeries format
        # Each fighter gets their own series with a single point (their max streak)
        for streak in streaks:
            if streak.last_win_date:
                trends.append(
                    TrendSeries(
                        metric_id="win_streak",
                        fighter_id=streak.fighter_id,
                        label=f"{streak.fighter_name} - Win Streak",
                        points=[
                            TrendPoint(
                                timestamp=streak.last_win_date.isoformat(),
                                value=float(streak.streak),
                            )
                        ],
                    )
                )

        # Transform average durations into TrendSeries format
        # Group by division to create time-series for each division
        duration_by_division: dict[str, list[TrendPoint]] = {}
        for duration in average_durations:
            division_key = duration.division or "All Divisions"
            if division_key not in duration_by_division:
                duration_by_division[division_key] = []
            duration_by_division[division_key].append(
                TrendPoint(
                    timestamp=duration.bucket_start.isoformat(),
                    value=duration.average_duration_minutes,
                )
            )

        # Create TrendSeries for each division
        for division, points in duration_by_division.items():
            # Sort points by timestamp
            points.sort(key=lambda p: p.timestamp)
            trends.append(
                TrendSeries(
                    metric_id=f"avg_duration_{division.lower().replace(' ', '_')}",
                    label=f"{division} - Average Fight Duration",
                    points=points,
                )
            )

        return TrendsResponse(trends=trends)

    async def _collect_leaderboard_entries(
        self,
        *,
        metric_name: str,
        eligible_fighters: Sequence[str] | None,
        limit: int,
    ) -> list[LeaderboardEntry]:
        """Collect leaderboard entries for a specific metric, casting values to floats."""

        value_column = self._numeric_stat_value()

        stmt = (
            select(
                fighter_stats.c.fighter_id,
                Fighter.name,
                Fighter.division,
                value_column.label("numeric_value"),
            )
            .join(Fighter, Fighter.id == fighter_stats.c.fighter_id)
            .where(fighter_stats.c.metric == metric_name)
        )

        if eligible_fighters is not None:
            stmt = stmt.where(fighter_stats.c.fighter_id.in_(eligible_fighters))

        stmt = (
            stmt.where(value_column.is_not(None))
            .order_by(value_column.desc())
            .limit(limit)
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        return [
            LeaderboardEntry(
                fighter_id=row.fighter_id,
                fighter_name=row.name,
                metric_value=float(row.numeric_value),
                detail_url=f"/fighters/{row.fighter_id}",
            )
            for row in rows
        ]

    def _numeric_stat_value(self):
        """Return an expression that casts the fighter stat value column to a float."""

        trimmed = func.trim(func.replace(fighter_stats.c.value, "%", ""))
        sanitized = func.nullif(trimmed, "")
        sanitized = func.nullif(sanitized, "--")
        return cast(sanitized, Float)

    async def _average_metric(self, metric_name: str) -> float | None:
        """Compute the average value for the given metric across all fighters."""

        value_column = self._numeric_stat_value()
        stmt = (
            select(func.avg(value_column))
            .where(fighter_stats.c.metric == metric_name)
            .where(value_column.is_not(None))
        )
        result = await self._session.execute(stmt)
        value = result.scalar()
        if value is None:
            return None
        return float(value)

    async def _calculate_win_streaks(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        limit: int,
    ) -> list[WinStreakSummary]:
        """Compute longest consecutive win streaks for fighters in the time range."""

        stmt = (
            select(
                Fight.fighter_id,
                Fighter.name,
                Fighter.division,
                Fight.event_date,
                Fight.result,
            )
            .join(Fighter, Fighter.id == Fight.fighter_id)
            .order_by(Fight.fighter_id, Fight.event_date)
        )

        if start_date is not None:
            stmt = stmt.where(Fight.event_date >= start_date)
        if end_date is not None:
            stmt = stmt.where(Fight.event_date <= end_date)

        result = await self._session.execute(stmt)
        rows = result.all()

        streaks: dict[str, WinStreakSummary] = {}
        active_streaks: dict[str, int] = {}
        for row in rows:
            fighter_id = row.fighter_id
            result_text = (row.result or "").strip().lower()
            is_win = result_text in {"w", "win"}

            if is_win:
                active = active_streaks.get(fighter_id, 0) + 1
                active_streaks[fighter_id] = active
                current_best = streaks.get(fighter_id)
                if current_best is None or active > current_best.streak:
                    streaks[fighter_id] = WinStreakSummary(
                        fighter_id=fighter_id,
                        fighter_name=row.name,
                        division=row.division,
                        streak=active,
                        last_win_date=row.event_date,
                    )
            else:
                active_streaks[fighter_id] = 0

        sorted_streaks = sorted(
            streaks.values(),
            key=lambda entry: (entry.streak, entry.last_win_date or date.min),
            reverse=True,
        )

        return sorted_streaks[:limit]

    async def _calculate_average_durations(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        time_bucket: str,
    ) -> list[AverageFightDuration]:
        """Compute average fight durations grouped by division and time bucket."""

        stmt = select(
            Fight.event_date,
            Fight.round,
            Fight.time,
            Fighter.division,
        ).join(Fighter, Fighter.id == Fight.fighter_id)

        if start_date is not None:
            stmt = stmt.where(Fight.event_date >= start_date)
        if end_date is not None:
            stmt = stmt.where(Fight.event_date <= end_date)

        result = await self._session.execute(stmt)
        rows = result.all()

        buckets: dict[tuple[str | None, date], dict[str, object]] = {}

        for row in rows:
            if row.event_date is None:
                continue
            duration = self._fight_duration_seconds(row.round, row.time)
            if duration is None:
                continue
            bucket_start, bucket_label = self._bucket_start(row.event_date, time_bucket)
            key = (row.division, bucket_start)
            entry = buckets.setdefault(key, {"label": bucket_label, "durations": []})
            durations = entry["durations"]
            assert isinstance(durations, list), (
                f"Expected the aggregated duration payload to be a list for key {key}, "
                f"received {type(durations)!r} instead."
            )
            durations.append(duration)

        averaged: list[AverageFightDuration] = []
        for (division, bucket_start), payload in buckets.items():
            durations = payload.get("durations")
            if not isinstance(durations, list) or not durations:
                continue
            avg_seconds = sum(durations) / len(durations)
            averaged.append(
                AverageFightDuration(
                    division=division,
                    bucket_start=bucket_start,
                    bucket_label=str(payload.get("label", "")),
                    average_duration_seconds=avg_seconds,
                    average_duration_minutes=avg_seconds / 60.0,
                )
            )

        averaged.sort(key=lambda entry: (entry.bucket_start, entry.division or ""))
        return averaged

    def _fight_duration_seconds(
        self, round_number: int | None, time_remaining: str | None
    ) -> float | None:
        """Translate fight round/time combination to elapsed seconds."""

        if round_number is None or time_remaining is None:
            return None

        try:
            minutes_str, seconds_str = time_remaining.split(":", maxsplit=1)
            minutes = int(minutes_str)
            seconds = int(seconds_str)
        except (ValueError, AttributeError):
            return None

        # Each regulation round is five minutes. Earlier rounds contribute full five minutes.
        regulation_round_seconds = 5 * 60
        elapsed_before_round = max(round_number - 1, 0) * regulation_round_seconds
        elapsed_this_round = minutes * 60 + seconds
        return float(elapsed_before_round + elapsed_this_round)

    def _bucket_start(self, event_date: date, bucket: str) -> tuple[date, str]:
        """Compute the bucket start date and label for the given resolution."""

        if bucket == "year":
            bucket_start = date(event_date.year, 1, 1)
            label = f"{event_date.year}"
        elif bucket == "quarter":
            quarter = (event_date.month - 1) // 3 + 1
            quarter_start_month = (quarter - 1) * 3 + 1
            bucket_start = date(event_date.year, quarter_start_month, 1)
            label = f"Q{quarter} {event_date.year}"
        else:
            bucket_start = date(event_date.year, event_date.month, 1)
            label = bucket_start.strftime("%b %Y")

        return bucket_start, label

    async def _fighters_active_between(
        self, start_date: date | None, end_date: date | None
    ) -> Sequence[str] | None:
        """Return fighter identifiers with fights in the supplied date window."""

        if start_date is None and end_date is None:
            return None

        stmt = select(Fight.fighter_id).group_by(Fight.fighter_id)
        if start_date is not None:
            stmt = stmt.where(Fight.event_date >= start_date)
        if end_date is not None:
            stmt = stmt.where(Fight.event_date <= end_date)

        result = await self._session.execute(stmt)
        return [row.fighter_id for row in result]

    async def get_random_fighter(self) -> FighterListItem | None:
        """Get a random fighter from the database."""
        query = select(Fighter).order_by(func.random()).limit(1)
        result = await self._session.execute(query)
        fighter = result.scalar_one_or_none()

        if fighter is None:
            return None

        return FighterListItem(
            fighter_id=fighter.id,
            detail_url=f"http://www.ufcstats.com/fighter-details/{fighter.id}",
            name=fighter.name,
            nickname=fighter.nickname,
            division=fighter.division,
            height=fighter.height,
            weight=fighter.weight,
            reach=fighter.reach,
            stance=fighter.stance,
            dob=fighter.dob,
            image_url=resolve_fighter_image(fighter.id, fighter.image_url),
        )


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
        for fight in event.fights:
            # Determine fighter names and IDs
            # Each fight has fighter_id and opponent_id
            fighter_1_id = fight.fighter_id
            fighter_2_id = fight.opponent_id

            # Get fighter names
            fighter_1_query = select(Fighter).where(Fighter.id == fighter_1_id)
            fighter_1_result = await self._session.execute(fighter_1_query)
            fighter_1 = fighter_1_result.scalar_one_or_none()

            fighter_1_name = fighter_1.name if fighter_1 else "Unknown"

            fighter_2_name = fight.opponent_name
            if fighter_2_id:
                fighter_2_query = select(Fighter).where(Fighter.id == fighter_2_id)
                fighter_2_result = await self._session.execute(fighter_2_query)
                fighter_2 = fighter_2_result.scalar_one_or_none()
                if fighter_2:
                    fighter_2_name = fighter_2.name

            fight_card.append(
                EventFight(
                    fight_id=fight.id,
                    fighter_1_id=fighter_1_id,
                    fighter_1_name=fighter_1_name,
                    fighter_2_id=fighter_2_id,
                    fighter_2_name=fighter_2_name,
                    weight_class=None,  # TODO: Extract from fight data
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
        return result.scalar_one()
