"""Stats repository for analytics and aggregate statistics.

This repository handles:
- Aggregate statistics (summary, leaderboards)
- Win streak calculations
- Time-series trends (month/quarter/year buckets)
- Fight duration analytics
- Performance metrics
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import Float, cast, func, select

from backend.db.models import Fight, Fighter, fighter_stats
from backend.db.repositories.base import BaseRepository
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


class StatsRepository(BaseRepository):
    """Repository for analytics and aggregate statistics."""

    async def stats_summary(self) -> StatsSummaryResponse:
        """Get aggregate statistics about fighters."""
        # Count total fighters
        count_query = select(func.count(Fighter.id))
        result = await self._session.execute(count_query)
        total_fighters = result.scalar_one_or_none() or 0

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
            .distinct(fighter_stats.c.fighter_id)
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
            if not isinstance(durations, list):
                message = (
                    "Expected the aggregated duration payload to be a list for key "
                    f"{key}, received {type(durations)!r} instead."
                )
                raise TypeError(message)
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
