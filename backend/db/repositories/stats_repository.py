"""Stats repository for analytics and aggregate statistics.

This repository handles:
- Aggregate statistics (summary, leaderboards)
- Win streak calculations
- Time-series trends (month/quarter/year buckets)
- Fight duration analytics
- Performance metrics
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import ClassVar

from sqlalchemy import Date, Float, Integer, case, cast, func, select
from sqlalchemy.sql import ColumnElement

from backend.db.models import Fight, Fighter, fighter_stats
from backend.db.repositories.base import BaseRepository
from backend.schemas.stats import (
    LEADERBOARD_METRIC_DESCRIPTIONS,
    SUMMARY_METRIC_DESCRIPTIONS,
    SUMMARY_METRIC_LABELS,
    AverageFightDuration,
    LeaderboardDefinition,
    LeaderboardEntry,
    LeaderboardMetricId,
    LeaderboardsResponse,
    StatsSummaryMetric,
    StatsSummaryMetricId,
    StatsSummaryResponse,
    TrendPoint,
    TrendSeries,
    TrendsResponse,
    TrendTimeBucket,
    WinStreakSummary,
)


@dataclass(frozen=True, slots=True)
class _LeaderboardPayload:
    """Lightweight container that pairs leaderboard metadata with ranked entries."""

    metric_id: str
    title: str
    description: str
    entries: Iterable[LeaderboardEntry]


class StatsRepository(BaseRepository):
    """Repository for analytics and aggregate statistics using SQL window functions."""

    _WIN_RESULTS: ClassVar[set[str]] = {"w", "win"}
    _SUMMARY_METRIC_PRECISION: ClassVar[Mapping[StatsSummaryMetricId, int]] = {
        "avg_sig_strikes_accuracy_pct": 1,
        "avg_takedown_accuracy_pct": 1,
        "avg_submission_attempts": 2,
    }

    async def stats_summary(self) -> StatsSummaryResponse:
        """Return dashboard friendly KPIs derived directly from SQL window functions."""

        metrics: list[StatsSummaryMetric] = []

        total_fighters_stmt = select(func.count(Fighter.id))
        total_fighters_result = await self._session.execute(total_fighters_stmt)
        total_fighters = int(total_fighters_result.scalar_one_or_none() or 0)
        metrics.append(
            StatsSummaryMetric(
                id="fighters_indexed",
                label=SUMMARY_METRIC_LABELS["fighters_indexed"],
                value=float(total_fighters),
                description=SUMMARY_METRIC_DESCRIPTIONS["fighters_indexed"],
            )
        )

        # Aggregate fighter_stats metrics with a windowed average so the SQL engine does all the
        # heavy lifting regardless of dataset size.
        metric_mapping: Mapping[str, StatsSummaryMetricId] = {
            "sig_strikes_accuracy_pct": "avg_sig_strikes_accuracy_pct",
            "takedown_accuracy_pct": "avg_takedown_accuracy_pct",
            "avg_submissions": "avg_submission_attempts",
        }
        metric_averages = await self._average_metrics(metric_mapping.keys())

        for source_metric, summary_id in metric_mapping.items():
            value = metric_averages.get(source_metric)
            if value is None:
                continue
            metrics.append(
                StatsSummaryMetric(
                    id=summary_id,
                    label=SUMMARY_METRIC_LABELS[summary_id],
                    value=round(
                        value,
                        self._SUMMARY_METRIC_PRECISION.get(summary_id, 1),
                    ),
                    description=SUMMARY_METRIC_DESCRIPTIONS[summary_id],
                )
            )

        avg_duration_seconds = await self._global_average_fight_duration_seconds()
        if avg_duration_seconds is not None:
            metrics.append(
                StatsSummaryMetric(
                    id="avg_fight_duration_minutes",
                    label=SUMMARY_METRIC_LABELS["avg_fight_duration_minutes"],
                    value=round(avg_duration_seconds / 60.0, 1),
                    description=SUMMARY_METRIC_DESCRIPTIONS[
                        "avg_fight_duration_minutes"
                    ],
                )
            )

        top_streaks = await self._calculate_win_streaks(
            start_date=None, end_date=None, limit=1
        )
        if top_streaks:
            longest = top_streaks[0]
            metrics.append(
                StatsSummaryMetric(
                    id="max_win_streak",
                    label=SUMMARY_METRIC_LABELS["max_win_streak"],
                    value=float(longest.streak),
                    description=SUMMARY_METRIC_DESCRIPTIONS["max_win_streak"],
                )
            )

        return StatsSummaryResponse(metrics=metrics)

    async def get_leaderboards(
        self,
        *,
        limit: int,
        offset: int,
        accuracy_metric: LeaderboardMetricId,
        submissions_metric: LeaderboardMetricId,
        division: str | None,
        min_fights: int | None,
        start_date: date | None,
        end_date: date | None,
    ) -> LeaderboardsResponse:
        """Compute leaderboards with filtering and pagination support."""

        leaderboards: list[_LeaderboardPayload] = []

        accuracy_entries = await self._collect_leaderboard_entries(
            metric_name=accuracy_metric,
            limit=limit,
            offset=offset,
            division=division,
            min_fights=min_fights,
            start_date=start_date,
            end_date=end_date,
        )
        if accuracy_entries:
            leaderboards.append(
                _LeaderboardPayload(
                    metric_id=accuracy_metric,
                    title="Striking Accuracy",
                    description=LEADERBOARD_METRIC_DESCRIPTIONS.get(
                        accuracy_metric, "Accuracy-focused leaderboard"
                    ),
                    entries=accuracy_entries,
                )
            )

        submissions_entries = await self._collect_leaderboard_entries(
            metric_name=submissions_metric,
            limit=limit,
            offset=offset,
            division=division,
            min_fights=min_fights,
            start_date=start_date,
            end_date=end_date,
        )
        if submissions_entries:
            leaderboards.append(
                _LeaderboardPayload(
                    metric_id=submissions_metric,
                    title="Submissions",
                    description=LEADERBOARD_METRIC_DESCRIPTIONS.get(
                        submissions_metric, "Submission-focused leaderboard"
                    ),
                    entries=submissions_entries,
                )
            )

        response_payload = [
            LeaderboardDefinition(
                metric_id=payload.metric_id,
                title=payload.title,
                description=payload.description,
                entries=list(payload.entries),
            )
            for payload in leaderboards
        ]

        return LeaderboardsResponse(leaderboards=response_payload)

    async def get_trends(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        time_bucket: TrendTimeBucket,
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

        for streak in streaks:
            if streak.last_win_date is None:
                continue
            trends.append(
                TrendSeries(
                    metric_id="win_streak",
                    fighter_id=streak.fighter_id,
                    label=f"{streak.fighter_name} • Win Streak",
                    points=[
                        TrendPoint(
                            timestamp=streak.last_win_date.isoformat(),
                            value=float(streak.streak),
                        )
                    ],
                )
            )

        duration_series: dict[str, list[TrendPoint]] = {}
        for duration in average_durations:
            division_label = duration.division or "All Divisions"
            duration_series.setdefault(division_label, []).append(
                TrendPoint(
                    timestamp=duration.bucket_start.isoformat(),
                    value=duration.average_duration_minutes,
                )
            )

        for division_label, points in duration_series.items():
            points.sort(key=lambda item: item.timestamp)
            slug = division_label.lower().replace(" ", "_")
            trends.append(
                TrendSeries(
                    metric_id=f"avg_fight_duration_{slug}",
                    label=f"{division_label} • Average Fight Duration",
                    points=points,
                )
            )

        return TrendsResponse(trends=trends)

    async def _collect_leaderboard_entries(
        self,
        *,
        metric_name: LeaderboardMetricId,
        limit: int,
        offset: int,
        division: str | None,
        min_fights: int | None,
        start_date: date | None,
        end_date: date | None,
    ) -> list[LeaderboardEntry]:
        """Collect leaderboard entries for a specific metric with filtering and pagination.

        This method deduplicates fighters by taking the maximum value for each fighter
        when multiple stat entries exist for the same metric.

        Supports filtering by:
        - division: Weight class filter
        - min_fights: Minimum number of UFC fights
        - start_date/end_date: Time range for fight filtering
        """

        numeric_value = self._numeric_stat_value()

        fight_exists = select(Fight.id).where(
            Fight.fighter_id == fighter_stats.c.fighter_id
        )
        if start_date is not None:
            fight_exists = fight_exists.where(Fight.event_date >= start_date)
        if end_date is not None:
            fight_exists = fight_exists.where(Fight.event_date <= end_date)

        # Correlated scalar subquery to count fights for each fighter
        fight_count_subq = (
            select(func.count(Fight.id))
            .where(Fight.fighter_id == fighter_stats.c.fighter_id)
            .where(Fight.event_date.isnot(None))
            .scalar_subquery()
        )

        # First, aggregate by fighter to handle duplicates (take max value per fighter)
        aggregated = (
            select(
                fighter_stats.c.fighter_id.label("fighter_id"),
                Fighter.name.label("fighter_name"),
                Fighter.division.label("division"),
                func.max(numeric_value).label("numeric_value"),
                func.max(fight_count_subq).label("fight_count"),
            )
            .join(Fighter, Fighter.id == fighter_stats.c.fighter_id)
            .where(fighter_stats.c.metric == metric_name)
            .where(numeric_value.isnot(None))
            .group_by(fighter_stats.c.fighter_id, Fighter.name, Fighter.division)
        )

        # Apply division filter
        if division is not None and division.strip():
            aggregated = aggregated.where(Fighter.division == division.strip())

        # Apply date range filter
        if start_date is not None or end_date is not None:
            aggregated = aggregated.where(fight_exists.exists())

        aggregated_subquery = aggregated.subquery()

        # Then rank the aggregated results
        ranked = (
            select(
                aggregated_subquery.c.fighter_id,
                aggregated_subquery.c.fighter_name,
                aggregated_subquery.c.numeric_value,
                aggregated_subquery.c.fight_count,
                func.row_number()
                .over(order_by=aggregated_subquery.c.numeric_value.desc())
                .label("rank"),
            )
        ).subquery()

        # Apply min_fights filter after aggregation
        stmt = select(
            ranked.c.fighter_id,
            ranked.c.fighter_name,
            ranked.c.numeric_value,
            ranked.c.fight_count,
            ranked.c.rank,
        )

        if min_fights is not None and min_fights > 0:
            stmt = stmt.where(ranked.c.fight_count >= min_fights)

        # Apply pagination
        stmt = (
            stmt.where(ranked.c.rank > offset)
            .where(ranked.c.rank <= offset + limit)
            .order_by(ranked.c.rank)
        )

        result = await self._session.execute(stmt)
        return [
            LeaderboardEntry(
                fighter_id=row.fighter_id,
                fighter_name=row.fighter_name,
                metric_value=float(row.numeric_value),
                detail_url=f"/fighters/{row.fighter_id}",
                fight_count=int(row.fight_count) if row.fight_count else None,
            )
            for row in result.fetchall()
        ]

    def _numeric_stat_value(self) -> ColumnElement[float | None]:
        """Return an expression that safely coerces the fighter stat value column to a float."""

        trimmed = func.trim(func.replace(fighter_stats.c.value, "%", ""))
        sanitized = func.nullif(trimmed, "")
        sanitized = func.nullif(sanitized, "--")
        return cast(sanitized, Float)

    async def _average_metrics(self, metrics: Iterable[str]) -> dict[str, float]:
        """Compute average values for each supplied metric using window functions."""

        metric_list = list(metrics)
        if not metric_list:
            return {}

        value_column = self._numeric_stat_value()
        windowed = (
            select(
                fighter_stats.c.metric.label("metric"),
                func.avg(value_column)
                .over(partition_by=fighter_stats.c.metric)
                .label("average_value"),
            )
            .where(fighter_stats.c.metric.in_(metric_list))
            .where(value_column.isnot(None))
        ).subquery()

        stmt = select(windowed.c.metric, windowed.c.average_value).distinct()
        result = await self._session.execute(stmt)
        return {row.metric: float(row.average_value) for row in result.fetchall()}

    async def _global_average_fight_duration_seconds(self) -> float | None:
        """Compute the global average fight duration (in seconds) via windowed aggregation."""

        duration_expr = self._fight_duration_seconds_expression()
        duration_cte = (
            select(
                duration_expr.label("duration_seconds"),
                func.avg(duration_expr).over().label("avg_duration"),
            ).where(duration_expr.isnot(None))
        ).cte("duration_stats")

        stmt = select(duration_cte.c.avg_duration).limit(1)
        result = await self._session.execute(stmt)
        value = result.scalar_one_or_none()
        return float(value) if value is not None else None

    async def _calculate_win_streaks(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        limit: int,
    ) -> list[WinStreakSummary]:
        """Compute longest consecutive win streaks for fighters in the time range."""

        win_flag = case(
            (func.lower(func.trim(Fight.result)).in_(self._WIN_RESULTS), 1),
            else_=0,
        ).label("is_win")

        ordered_fights = (
            select(
                Fight.fighter_id.label("fighter_id"),
                Fighter.name.label("fighter_name"),
                Fighter.division.label("division"),
                Fight.event_date.label("event_date"),
                win_flag,
                func.row_number()
                .over(partition_by=Fight.fighter_id, order_by=Fight.event_date)
                .label("row_number"),
                func.sum(win_flag)
                .over(partition_by=Fight.fighter_id, order_by=Fight.event_date)
                .label("wins_to_date"),
            )
            .join(Fighter, Fighter.id == Fight.fighter_id)
            .where(Fight.event_date.isnot(None))
        )

        if start_date is not None:
            ordered_fights = ordered_fights.where(Fight.event_date >= start_date)
        if end_date is not None:
            ordered_fights = ordered_fights.where(Fight.event_date <= end_date)

        ordered_cte = ordered_fights.cte("ordered_fights")

        streak_groups = (
            select(
                ordered_cte.c.fighter_id,
                ordered_cte.c.fighter_name,
                ordered_cte.c.division,
                ordered_cte.c.event_date,
                ordered_cte.c.is_win,
                (ordered_cte.c.row_number - ordered_cte.c.wins_to_date).label(
                    "streak_group"
                ),
            )
        ).cte("streak_groups")

        streak_aggregates = (
            select(
                streak_groups.c.fighter_id,
                streak_groups.c.fighter_name,
                streak_groups.c.division,
                func.count().label("streak_length"),
                func.max(streak_groups.c.event_date).label("last_win_date"),
            )
            .where(streak_groups.c.is_win == 1)
            .group_by(
                streak_groups.c.fighter_id,
                streak_groups.c.fighter_name,
                streak_groups.c.division,
                streak_groups.c.streak_group,
            )
        ).cte("streak_aggregates")

        ranked = (
            select(
                streak_aggregates.c.fighter_id,
                streak_aggregates.c.fighter_name,
                streak_aggregates.c.division,
                streak_aggregates.c.streak_length,
                streak_aggregates.c.last_win_date,
                func.row_number()
                .over(
                    order_by=(
                        streak_aggregates.c.streak_length.desc(),
                        streak_aggregates.c.last_win_date.desc(),
                    )
                )
                .label("streak_rank"),
            )
        ).subquery()

        stmt = (
            select(
                ranked.c.fighter_id,
                ranked.c.fighter_name,
                ranked.c.division,
                ranked.c.streak_length,
                ranked.c.last_win_date,
            )
            .where(ranked.c.streak_rank <= limit)
            .order_by(
                ranked.c.streak_length.desc(),
                ranked.c.last_win_date.desc(),
                ranked.c.fighter_name,
            )
        )

        result = await self._session.execute(stmt)
        return [
            WinStreakSummary(
                fighter_id=row.fighter_id,
                fighter_name=row.fighter_name,
                division=row.division,
                streak=int(row.streak_length),
                last_win_date=row.last_win_date,
            )
            for row in result.fetchall()
        ]

    async def _calculate_average_durations(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        time_bucket: TrendTimeBucket,
    ) -> list[AverageFightDuration]:
        """Compute average fight durations grouped by division and temporal bucket."""

        duration_expr = self._fight_duration_seconds_expression()
        bucket_expr = self._bucket_start_expression(time_bucket)

        base_query = (
            select(
                Fighter.division.label("division"),
                bucket_expr.label("bucket_start"),
                duration_expr.label("duration_seconds"),
            )
            .join(Fighter, Fighter.id == Fight.fighter_id)
            .where(duration_expr.isnot(None))
            .where(Fight.event_date.isnot(None))
        )

        if start_date is not None:
            base_query = base_query.where(Fight.event_date >= start_date)
        if end_date is not None:
            base_query = base_query.where(Fight.event_date <= end_date)

        base_cte = base_query.cte("duration_base")

        windowed = (
            select(
                base_cte.c.division,
                base_cte.c.bucket_start,
                func.avg(base_cte.c.duration_seconds)
                .over(partition_by=(base_cte.c.division, base_cte.c.bucket_start))
                .label("avg_duration"),
            )
        ).subquery()

        stmt = select(
            windowed.c.division, windowed.c.bucket_start, windowed.c.avg_duration
        ).distinct()

        result = await self._session.execute(stmt)
        durations: list[AverageFightDuration] = []
        for row in result.fetchall():
            bucket_start_value = row.bucket_start
            if bucket_start_value is None:
                continue
            if isinstance(bucket_start_value, datetime):
                bucket_start_date = bucket_start_value.date()
            elif isinstance(bucket_start_value, date):
                bucket_start_date = bucket_start_value
            else:
                bucket_start_date = date.fromisoformat(str(bucket_start_value))
            durations.append(
                AverageFightDuration(
                    division=row.division,
                    bucket_start=bucket_start_date,
                    bucket_label=self._format_bucket_label(
                        bucket_start_date, time_bucket
                    ),
                    average_duration_seconds=float(row.avg_duration),
                    average_duration_minutes=float(row.avg_duration) / 60.0,
                )
            )

        durations.sort(key=lambda entry: (entry.bucket_start, entry.division or ""))
        return durations

    def _fight_duration_seconds_expression(self) -> ColumnElement[float | None]:
        """Translate fight round/time combination to elapsed seconds using PostgreSQL functions."""

        raw_minutes = func.split_part(Fight.time, ":", 1)
        raw_seconds = func.split_part(Fight.time, ":", 2)

        minute_text = func.nullif(func.nullif(raw_minutes, ""), "--")
        second_text = func.nullif(func.nullif(raw_seconds, ""), "--")

        valid_time = (
            Fight.time.isnot(None)
            & minute_text.isnot(None)
            & second_text.isnot(None)
            & Fight.round.isnot(None)
        )

        round_index = func.coalesce(Fight.round, 1)
        completed_rounds = case((round_index > 1, round_index - 1), else_=0)
        elapsed_before_round = completed_rounds * 300
        elapsed_this_round = cast(minute_text, Integer) * 60 + cast(
            second_text, Integer
        )

        return case(
            (valid_time, cast(elapsed_before_round + elapsed_this_round, Float)),
            else_=None,
        )

    def _bucket_start_expression(self, bucket: TrendTimeBucket) -> ColumnElement[date]:
        """Return the PostgreSQL date_trunc bucket start for the requested interval."""

        truncate_unit = {"year": "year", "quarter": "quarter"}.get(bucket, "month")
        return cast(func.date_trunc(truncate_unit, Fight.event_date), Date)

    def _format_bucket_label(self, bucket_start: date, bucket: TrendTimeBucket) -> str:
        """Format a human readable label for the supplied bucket start."""

        if bucket == "year":
            return f"{bucket_start.year}"
        if bucket == "quarter":
            quarter = (bucket_start.month - 1) // 3 + 1
            return f"Q{quarter} {bucket_start.year}"
        return bucket_start.strftime("%b %Y")
