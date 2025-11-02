from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date

from sqlalchemy import Float, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.models import Fight, Fighter, fighter_stats
from backend.schemas.fighter import FighterDetail, FighterListItem, FightHistoryEntry
from backend.schemas.stats import (
    AverageFightDuration,
    LeaderboardEntry,
    LeaderboardsResponse,
    MetricLeaderboard,
    TrendsResponse,
    WinStreakSummary,
)


class PostgreSQLFighterRepository:
    """Repository for fighter data using PostgreSQL database."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_fighters(
        self, *, limit: int | None = None, offset: int | None = None
    ) -> Iterable[FighterListItem]:
        """List all fighters with optional pagination."""
        query = select(Fighter)

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
                division=fighter.division,
                height=fighter.height,
                weight=fighter.weight,
                reach=fighter.reach,
                stance=fighter.stance,
                dob=fighter.dob,
            )
            for fighter in fighters
        ]

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Get detailed fighter information by ID."""
        query = (
            select(Fighter)
            .where(Fighter.id == fighter_id)
            .options(selectinload(Fighter.fights))
        )
        result = await self._session.execute(query)
        fighter = result.scalar_one_or_none()

        if fighter is None:
            return None

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

        # Convert fights to FightHistoryEntry
        fight_history = [
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
            for fight in fighter.fights
        ]

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
            record=fighter.record,
            leg_reach=fighter.leg_reach,
            division=fighter.division,
            age=None,  # TODO: Calculate age from dob
            striking=stats_map.get("striking", {}),
            grappling=stats_map.get("grappling", {}),
            significant_strikes=stats_map.get("significant_strikes", {}),
            takedown_stats=stats_map.get("takedown_stats", {}),
            fight_history=fight_history,
        )

    async def stats_summary(self) -> dict[str, float]:
        """Get aggregate statistics about fighters."""
        # Count total fighters
        count_query = select(func.count(Fighter.id))
        result = await self._session.execute(count_query)
        total_fighters = result.scalar() or 0

        return {
            "fighters_indexed": float(total_fighters),
        }

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
        self, query: str | None = None, stance: str | None = None
    ) -> Iterable[FighterListItem]:
        """Search fighters by name or filter by stance."""
        stmt = select(Fighter)

        if query:
            stmt = stmt.where(
                (Fighter.name.ilike(f"%{query}%"))
                | (Fighter.nickname.ilike(f"%{query}%"))
            )

        if stance:
            stmt = stmt.where(Fighter.stance == stance)

        result = await self._session.execute(stmt)
        fighters = result.scalars().all()

        return [
            FighterListItem(
                fighter_id=fighter.id,
                detail_url=f"http://www.ufcstats.com/fighter-details/{fighter.id}",
                name=fighter.name,
                nickname=fighter.nickname,
                height=fighter.height,
                weight=fighter.weight,
                reach=fighter.reach,
                stance=fighter.stance,
                dob=fighter.dob,
                division=fighter.division,
            )
            for fighter in fighters
        ]

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

        return LeaderboardsResponse(
            accuracy=MetricLeaderboard(
                metric=accuracy_metric, entries=accuracy_entries
            ),
            submissions=MetricLeaderboard(
                metric=submissions_metric, entries=submissions_entries
            ),
        )

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

        return TrendsResponse(
            longest_win_streaks=streaks, average_fight_durations=average_durations
        )

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
                division=row.division,
                metric=metric_name,
                value=float(row.numeric_value),
            )
            for row in rows
        ]

    def _numeric_stat_value(self):
        """Return an expression that casts the fighter stat value column to a float."""

        trimmed = func.trim(func.replace(fighter_stats.c.value, "%", ""))
        sanitized = func.nullif(trimmed, "")
        sanitized = func.nullif(sanitized, "--")
        return cast(sanitized, Float)

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
            assert isinstance(durations, list)
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
        )
