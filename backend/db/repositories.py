from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime
from typing import Any, Literal
from typing import cast as typing_cast

from sqlalchemy import Float, cast, desc, func, inspect, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

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
from backend.services.image_resolver import (
    resolve_fighter_image,
    resolve_fighter_image_cropped,
)
from backend.utils.event_utils import detect_event_type


_WAS_INTERIM_SUPPORTED_CACHE: bool | None = None


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

    # Calculate years difference
    years_elapsed = reference_date.year - dob.year

    # Check if birthday has occurred this year
    has_had_birthday = (reference_date.month, reference_date.day) >= (
        dob.month,
        dob.day,
    )

    return years_elapsed - (not has_had_birthday)


class PostgreSQLFighterRepository:
    """Repository for fighter data using PostgreSQL database."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._was_interim_supported: bool | None = None

    async def _supports_was_interim(self) -> bool:
        global _WAS_INTERIM_SUPPORTED_CACHE

        if _WAS_INTERIM_SUPPORTED_CACHE is not None:
            self._was_interim_supported = _WAS_INTERIM_SUPPORTED_CACHE
            return _WAS_INTERIM_SUPPORTED_CACHE

        if self._was_interim_supported is not None:
            return self._was_interim_supported

        def check(sync_session: Any) -> bool:
            bind = sync_session.get_bind()
            inspector = inspect(bind)
            columns = inspector.get_columns(Fighter.__tablename__)
            return any(column["name"] == "was_interim" for column in columns)

        try:
            self._was_interim_supported = await self._session.run_sync(check)
        except Exception:
            self._was_interim_supported = False

        _WAS_INTERIM_SUPPORTED_CACHE = self._was_interim_supported
        return self._was_interim_supported

    async def _resolve_fighter_columns(
        self,
        base_columns: Sequence[Any],
        *,
        include_was_interim: bool = True,
    ) -> tuple[list[Any], bool]:
        supports_was_interim = await self._supports_was_interim()
        columns = list(base_columns)
        if include_was_interim and supports_was_interim:
            columns.append(Fighter.was_interim)
        return columns, supports_was_interim

    def _fighter_summary_columns(self) -> list[Any]:
        return [
            Fighter.id,
            Fighter.name,
            Fighter.nickname,
            Fighter.record,
            Fighter.division,
            Fighter.height,
            Fighter.weight,
            Fighter.reach,
            Fighter.stance,
            Fighter.dob,
            Fighter.image_url,
            Fighter.is_current_champion,
            Fighter.is_former_champion,
        ]

    async def _batch_compute_streaks(
        self,
        fighter_ids: list[str],
        *,
        window: int | None = 6,
    ) -> dict[str, dict[str, int | Literal["win", "loss", "draw", "none"]]]:
        """Compute streaks for multiple fighters in a single database query.

        Returns a dictionary mapping fighter_id to their streak info.
        This is much more efficient than calling _compute_current_streak for each fighter.
        """
        if not fighter_ids:
            return {}

        effective_window: int | None = None if window is None else max(2, window)

        subject_stmt = (
            select(
                Fight.fighter_id.label("subject_id"),
                Fight.event_date.label("event_date"),
                Fight.result.label("result"),
                literal(True).label("is_primary"),
            ).where(Fight.fighter_id.in_(fighter_ids))
        )
        opponent_stmt = (
            select(
                Fight.opponent_id.label("subject_id"),
                Fight.event_date.label("event_date"),
                Fight.result.label("result"),
                literal(False).label("is_primary"),
            )
            .where(Fight.opponent_id.in_(fighter_ids))
            .where(Fight.opponent_id.is_not(None))
        )

        unified = union_all(subject_stmt, opponent_stmt).subquery("subject_fights")

        order_clause = unified.c.event_date.desc().nulls_last()

        if effective_window is not None:
            ranked = (
                select(
                    unified.c.subject_id,
                    unified.c.event_date,
                    unified.c.result,
                    unified.c.is_primary,
                    func.row_number()
                    .over(
                        partition_by=unified.c.subject_id,
                        order_by=order_clause,
                    )
                    .label("row_number"),
                )
            ).subquery("ranked_subject_fights")

            stmt = (
                select(
                    ranked.c.subject_id,
                    ranked.c.event_date,
                    ranked.c.result,
                    ranked.c.is_primary,
                )
                .where(ranked.c.row_number <= effective_window)
                .order_by(ranked.c.subject_id, ranked.c.event_date.desc().nulls_last())
            )
        else:
            stmt = select(
                unified.c.subject_id,
                unified.c.event_date,
                unified.c.result,
                unified.c.is_primary,
            ).order_by(unified.c.subject_id, order_clause)

        result = await self._session.execute(stmt)
        all_fights = result.all()

        # Group fights by fighter in memory
        fights_by_fighter: dict[str, list[tuple[date | None, str]]] = {
            fid: [] for fid in fighter_ids
        }

        for subject_id, event_date, result_text, is_primary in all_fights:
            if subject_id not in fights_by_fighter:
                continue
            normalized_result = result_text or ""
            if not bool(is_primary):
                normalized_result = _invert_fight_result(normalized_result)
            fights_by_fighter[subject_id].append((event_date, normalized_result))

        # Compute streaks for each fighter
        streaks = {}
        for fighter_id, fight_entries in fights_by_fighter.items():
            streaks[fighter_id] = self._compute_streak_from_fights(
                fight_entries, effective_window
            )

        return streaks

    def _compute_streak_from_fights(
        self,
        fight_entries: list[tuple[date | None, str]],
        window: int | None,
    ) -> dict[str, int | Literal["win", "loss", "draw", "none"]]:
        """Compute streak from a list of fight entries (date, result pairs).

        This is extracted from _compute_current_streak to allow reuse in batch operations.
        """
        if not fight_entries:
            return {"current_streak_type": "none", "current_streak_count": 0}

        # Sort by date descending (most recent first)
        fight_entries.sort(
            key=lambda entry: (entry[0] is None, entry[0] or date.min), reverse=True
        )

        # Find the last completed result type
        last_completed: Literal["win", "loss", "draw"] | None = None
        completed_seen = 0
        for _, result_text in fight_entries:
            category = _normalize_result_category(result_text)
            if category in {"win", "loss", "draw"}:
                last_completed = typing_cast(
                    Literal["win", "loss", "draw"], category
                )
                break
        if last_completed is None:
            return {"current_streak_type": "none", "current_streak_count": 0}

        consecutive = 0
        for _, result_text in fight_entries:
            category = _normalize_result_category(result_text)
            if category == last_completed:
                consecutive += 1
                completed_seen += 1
            elif category in {"win", "loss", "draw"}:
                break
            else:
                continue
            if window is not None and completed_seen >= window:
                break

        if consecutive < 2:
            return {"current_streak_type": "none", "current_streak_count": 0}

        return {
            "current_streak_type": last_completed,
            "current_streak_count": consecutive,
        }

    async def _compute_current_streak(
        self,
        fighter_id: str,
        *,
        window: int = 6,
    ) -> dict[str, int | Literal["win", "loss", "draw", "none"]]:
        """Return the most recent decisive streak for ``fighter_id``.

        Note: For multiple fighters, use _batch_compute_streaks() instead for better performance.
        """
        # Use the batch method for consistency
        result = await self._batch_compute_streaks([fighter_id], window=window)
        return result.get(fighter_id, {"current_streak_type": "none", "current_streak_count": 0})

    def _fighter_detail_columns(self) -> list[Any]:
        return [
            Fighter.id,
            Fighter.name,
            Fighter.nickname,
            Fighter.height,
            Fighter.weight,
            Fighter.reach,
            Fighter.stance,
            Fighter.dob,
            Fighter.image_url,
            Fighter.record,
            Fighter.leg_reach,
            Fighter.division,
            Fighter.is_current_champion,
            Fighter.is_former_champion,
            Fighter.championship_history,
        ]

    def _fighter_comparison_columns(self) -> list[Any]:
        return [
            Fighter.id,
            Fighter.name,
            Fighter.record,
            Fighter.division,
            Fighter.image_url,
            Fighter.is_current_champion,
            Fighter.is_former_champion,
        ]

    async def list_fighters(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        include_streak: bool = False,
        streak_window: int = 6,
    ) -> Iterable[FighterListItem]:
        """List all fighters with optional pagination.

        When ``include_streak`` is True, compute a lightweight current streak summary for
        the fighters returned on this page only. The computation uses at most
        ``streak_window`` most recent completed fights (ignores upcoming/NC/other results).
        """
        base_columns = self._fighter_summary_columns()
        load_columns, supports_was_interim = await self._resolve_fighter_columns(
            base_columns
        )

        query = (
            select(Fighter)
            .options(load_only(*load_columns))
            .order_by(Fighter.name, Fighter.id)
        )

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        result = await self._session.execute(query)
        fighters = result.scalars().all()

        # Optionally compute current streaks for the returned fighters only
        streak_by_fighter: dict[str, dict[str, int | Literal["win", "loss", "draw", "none"]]] = {}
        if include_streak and fighters:
            fighter_ids = [f.id for f in fighters]
            streak_by_fighter = await self._batch_compute_streaks(
                fighter_ids, window=streak_window
            )

        # Cache a single "today" value in UTC so every fighter on the page uses
        # the same reference point for age calculations.
        today_utc: date = datetime.now(tz=UTC).date()

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
                age=_calculate_age(
                    dob=fighter.dob,
                    reference_date=today_utc,
                ),
                is_current_champion=fighter.is_current_champion,
                is_former_champion=fighter.is_former_champion,
                was_interim=fighter.was_interim if supports_was_interim else False,
                current_streak_type=typing_cast(
                    Literal["win", "loss", "draw", "none"],
                    (
                        streak_by_fighter.get(fighter.id, {}).get("current_streak_type", "none")
                        if include_streak
                        else "none"
                    ),
                ),
                current_streak_count=(
                    int(streak_by_fighter.get(fighter.id, {}).get("current_streak_count", 0))
                    if include_streak
                    else 0
                ),
            )
            for fighter in fighters
        ]

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Get detailed fighter information by ID with eager-loaded relationships."""
        # Query fighter details with eager-loaded fights
        base_columns = self._fighter_detail_columns()
        load_columns, supports_was_interim = await self._resolve_fighter_columns(
            base_columns
        )
        fighter_query = (
            select(Fighter)
            .options(
                load_only(*load_columns),
                selectinload(Fighter.fights),  # Eager load fights relationship
            )
            .where(Fighter.id == fighter_id)
        )
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
        fight_breakdowns: dict[str, dict[str, Any]] = {}
        for category, metric, value in stats_result.all():
            if category == "fight_history":
                if metric and value:
                    try:
                        decoded = json.loads(value)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(decoded, dict):
                        fight_breakdowns[metric] = decoded
                continue
            if category is None or metric is None or value is None:
                continue
            category_stats = stats_map.setdefault(category, {})
            category_stats[metric] = value

        # Query fights from BOTH perspectives:
        # 1. Fights where this fighter is fighter_id (already loaded via relationship)
        # 2. Fights where this fighter is opponent_id
        fights_query = select(Fight).where(
            (Fight.fighter_id == fighter_id) | (Fight.opponent_id == fighter_id)
        )
        fights_result = await self._session.execute(fights_query)
        all_fights = fights_result.scalars().all()

        # Build fight history, deduplicating by fight metadata (not database ID)
        # This prevents duplicate entries when both fighters have Fight records for the same bout
        # Prioritize fights where fighter_id matches (fighter's own perspective)
        # Also prioritize fights with actual results (win/loss/draw) over "N/A"
        fight_dict: dict[tuple[str, str | None, str], FightHistoryEntry] = {}

        def create_fight_key(
            event_name: str,
            event_date: date | None,
            opponent_id: str | None,
            opponent_name: str,
        ) -> tuple[str, str | None, str]:
            """Create a unique key for deduplication based on fight metadata."""
            date_str = event_date.isoformat() if event_date else None
            # Use opponent_id if available, otherwise use opponent_name (normalized)
            opponent_key = opponent_id if opponent_id else opponent_name.lower().strip()
            return (event_name, date_str, opponent_key)

        def should_replace_fight(existing_result: str, new_result: str) -> bool:
            """Determine if new fight should replace existing based on result quality."""
            # Prefer actual results (win/loss/draw) over "N/A"
            if existing_result == "N/A" and new_result != "N/A":
                return True
            return False

        def merge_fight_stats(fight_id: str, base_stats: Any) -> dict[str, Any]:
            """Combine inline fight stats with cached fighter_stats payloads."""

            base: dict[str, Any]
            if isinstance(base_stats, dict):
                base = dict(base_stats)
            else:
                base = {}

            breakdown = fight_breakdowns.get(fight_id)
            if not breakdown:
                return base

            extra_stats = breakdown.get("stats")
            if isinstance(extra_stats, dict) and extra_stats:
                base.update(extra_stats)
            return base

        def enrich_field(
            original: Any, breakdown: dict[str, Any] | None, key: str
        ) -> Any:
            """Use cached fight metadata when the ``Fight`` row lacks detail."""

            if original not in (None, "", "Unknown"):
                return original
            if breakdown is None:
                return original
            candidate = breakdown.get(key)
            if candidate in (None, "", "--"):
                return original
            return candidate

        # First pass: Process fights where this fighter is the primary fighter_id
        for fight in all_fights:
            if fight.fighter_id == fighter_id:
                fight_key = create_fight_key(
                    fight.event_name,
                    fight.event_date,
                    fight.opponent_id,
                    fight.opponent_name,
                )

                breakdown = fight_breakdowns.get(fight.id)
                stats_payload = merge_fight_stats(fight.id, fight.stats)

                new_entry = FightHistoryEntry(
                    fight_id=fight.id,
                    event_name=enrich_field(fight.event_name, breakdown, "event_name"),
                    event_date=fight.event_date,
                    opponent=enrich_field(fight.opponent_name, breakdown, "opponent"),
                    opponent_id=enrich_field(
                        fight.opponent_id, breakdown, "opponent_id"
                    ),
                    result=enrich_field(fight.result, breakdown, "result"),
                    method=enrich_field(fight.method or "", breakdown, "method"),
                    round=enrich_field(fight.round, breakdown, "round"),
                    time=enrich_field(fight.time, breakdown, "time"),
                    fight_card_url=enrich_field(
                        fight.fight_card_url, breakdown, "fight_card_url"
                    ),
                    stats=stats_payload,
                )

                if fight_key not in fight_dict:
                    fight_dict[fight_key] = new_entry
                elif should_replace_fight(fight_dict[fight_key].result, fight.result):
                    # Replace with better result
                    fight_dict[fight_key] = new_entry

        # Collect unique opponent identifiers to collapse the legacy N+1 pattern
        # into a single batched lookup against the fighters table.
        opponent_ids: set[str] = set()
        for fight in all_fights:
            # Only collect IDs of actual opponents
            if fight.fighter_id == fighter_id and fight.opponent_id:
                opponent_ids.add(fight.opponent_id)
            elif fight.opponent_id == fighter_id and fight.fighter_id:
                opponent_ids.add(fight.fighter_id)
        opponent_lookup: dict[str, str] = {}
        if opponent_ids:
            opponent_rows = await self._session.execute(
                select(Fighter.id, Fighter.name).where(Fighter.id.in_(opponent_ids))
            )
            opponent_lookup = {row.id: row.name for row in opponent_rows.all()}

        # Second pass: Process fights from opponent's perspective (only if not already seen)
        for fight in all_fights:
            if fight.fighter_id != fighter_id:
                opponent_name = opponent_lookup.get(fight.fighter_id, "Unknown")
                opponent_id = fight.fighter_id

                fight_key = create_fight_key(
                    fight.event_name, fight.event_date, opponent_id, opponent_name
                )

                # Invert the result
                inverted_result = _invert_fight_result(fight.result)

                breakdown = fight_breakdowns.get(fight.id)
                stats_payload = merge_fight_stats(fight.id, fight.stats)

                new_entry = FightHistoryEntry(
                    fight_id=fight.id,
                    event_name=enrich_field(fight.event_name, breakdown, "event_name"),
                    event_date=fight.event_date,
                    opponent=opponent_name,
                    opponent_id=opponent_id,  # The original fighter_id is now the opponent
                    result=inverted_result,
                    method=enrich_field(fight.method or "", breakdown, "method"),
                    round=enrich_field(fight.round, breakdown, "round"),
                    time=enrich_field(fight.time, breakdown, "time"),
                    fight_card_url=enrich_field(
                        fight.fight_card_url, breakdown, "fight_card_url"
                    ),
                    stats=stats_payload,
                )

                if fight_key not in fight_dict:
                    fight_dict[fight_key] = new_entry
                elif should_replace_fight(
                    fight_dict[fight_key].result, inverted_result
                ):
                    # Replace with better result
                    fight_dict[fight_key] = new_entry

        # Convert dict to list
        fight_history: list[FightHistoryEntry] = list(fight_dict.values())

        # Sort fight history: upcoming fights first, then past fights by most recent
        fight_history.sort(
            key=lambda fight: (
                # Primary: upcoming fights first (result="next" → 0, others → 1)
                0 if fight.result == "next" else 1,
                # Secondary: most recent first (use min date for nulls to push them last)
                -(fight.event_date or date.min).toordinal(),
            )
        )

        # Compute record from fight_history if not already populated
        computed_record = fighter.record
        if not computed_record and fight_history:
            wins = sum(
                1
                for fight in fight_history
                if _normalize_result_category(fight.result) == "win"
            )
            losses = sum(
                1
                for fight in fight_history
                if _normalize_result_category(fight.result) == "loss"
            )
            draws = sum(
                1
                for fight in fight_history
                if _normalize_result_category(fight.result) == "draw"
            )
            # Only set computed record if we found at least one completed fight
            if wins + losses + draws > 0:
                computed_record = f"{wins}-{losses}-{draws}"

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
            record=computed_record,
            leg_reach=fighter.leg_reach,
            division=fighter.division,
            age=fighter_age,
            striking=stats_map.get("striking", {}),
            grappling=stats_map.get("grappling", {}),
            significant_strikes=stats_map.get("significant_strikes", {}),
            takedown_stats=stats_map.get("takedown_stats", {}),
            career=stats_map.get("career", {}),
            fight_history=fight_history,
            is_current_champion=fighter.is_current_champion,
            is_former_champion=fighter.is_former_champion,
            was_interim=fighter.was_interim if supports_was_interim else False,
            championship_history=fighter.championship_history or {},
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
            fallback_query = (
                select(
                    Fighter.id,
                    Fighter.name,
                    Fighter.division,
                    Fighter.record,
                    Fighter.image_url,
                    Fighter.cropped_image_url,
                ).order_by(Fighter.name, Fighter.id)
            )
            if division:
                fallback_query = fallback_query.where(Fighter.division == division)
            if limit is not None:
                fallback_query = fallback_query.limit(limit)
            fallback_result = await self._session.execute(fallback_query)
            fallback_fighters = fallback_result.all()
            nodes = [
                FightGraphNode(
                    fighter_id=row.id,
                    name=row.name,
                    division=row.division,
                    record=row.record,
                    image_url=resolve_fighter_image_cropped(
                        row.id, row.image_url, row.cropped_image_url
                    ),
                    total_fights=0,
                    latest_event_date=None,
                )
                for row in fallback_fighters
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

        fighters_query = select(
            Fighter.id,
            Fighter.name,
            Fighter.division,
            Fighter.record,
            Fighter.image_url,
            Fighter.cropped_image_url,
        ).where(Fighter.id.in_(id_order))
        fighters_result = await self._session.execute(fighters_query)
        fighters = fighters_result.all()
        fighter_map = {row.id: row for row in fighters}

        nodes: list[FightGraphNode] = []
        for fighter_id in id_order:
            fighter_row = fighter_map.get(fighter_id)
            if fighter_row is None:
                continue
            nodes.append(
                FightGraphNode(
                    fighter_id=fighter_row.id,
                    name=fighter_row.name,
                    division=fighter_row.division,
                    record=fighter_row.record,
                    image_url=resolve_fighter_image_cropped(
                        fighter_row.id,
                        fighter_row.image_url,
                        fighter_row.cropped_image_url,
                    ),
                    total_fights=count_map.get(fighter_row.id, 0),
                    latest_event_date=latest_map.get(fighter_row.id),
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

    async def create_fighter(self, fighter: Fighter) -> Fighter:
        """Create a new fighter in the database."""
        self._session.add(fighter)
        await self._session.flush()
        return fighter

    async def upsert_fighter(self, fighter_data: dict) -> Fighter:
        """Insert or update a fighter based on ID."""
        fighter_id = fighter_data.get("id")

        # Check if fighter exists
        query = (
            select(Fighter)
            .options(load_only(Fighter.id))
            .where(Fighter.id == fighter_id)
        )
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
        champion_statuses: list[str] | None = None,
        streak_type: str | None = None,
        min_streak_count: int | None = None,
        include_streak: bool = False,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[list[FighterListItem], int]:
        """Search fighters by name, stance, division, champion status, or streak.

        Supports pagination with limit and offset parameters.
        """

        filters = []
        if query:
            # Use ILIKE for case-insensitive search
            # This works with PostgreSQL trigram indexes (pg_trgm) for 10x speedup
            # Falls back to standard LIKE behavior in SQLite
            pattern = f"%{query}%"
            filters.append(
                (Fighter.name.ilike(pattern))
                | (Fighter.nickname.ilike(pattern))
            )
        if stance:
            filters.append(Fighter.stance == stance)
        if division:
            filters.append(Fighter.division == division)
        if champion_statuses:
            # Build OR conditions for multiple champion statuses
            champion_conditions = []
            for status in champion_statuses:
                if status == "current":
                    champion_conditions.append(Fighter.is_current_champion.is_(True))
                elif status == "former":
                    champion_conditions.append(Fighter.is_former_champion.is_(True))
            if champion_conditions:
                # Use OR to combine conditions (show fighters matching ANY status)
                from sqlalchemy import or_

                filters.append(or_(*champion_conditions))

        apply_streak_filter = bool(streak_type and min_streak_count)

        base_columns = self._fighter_summary_columns()
        load_columns, supports_was_interim = await self._resolve_fighter_columns(
            base_columns
        )
        stmt = (
            select(Fighter)
            .options(load_only(*load_columns))
            .order_by(Fighter.name)
        )
        count_stmt = select(func.count()).select_from(Fighter)

        for condition in filters:
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        if not apply_streak_filter:
            if offset is not None and offset > 0:
                stmt = stmt.offset(offset)
            if limit is not None and limit > 0:
                stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        fighters = result.scalars().all()

        # Use a single "today" snapshot so every returned card displays the same
        # age even if the request straddles midnight in UTC.
        today_utc: date = datetime.now(tz=UTC).date()

        # Calculate streaks if needed (either for filtering or for including in response)
        # Use batch computation for better performance (100x speedup)
        fighter_streaks = {}
        if include_streak or apply_streak_filter:
            fighter_ids = [f.id for f in fighters]
            if apply_streak_filter:
                threshold = max(2, (min_streak_count or 1) + 1)
                streak_window = threshold
            else:
                streak_window = 6
            fighter_streaks = await self._batch_compute_streaks(
                fighter_ids, window=streak_window
            )

        # Apply streak filtering if requested
        if apply_streak_filter:
            filtered_fighters = []
            for fighter in fighters:
                streak_info = fighter_streaks.get(fighter.id, {})
                if (
                    streak_info.get("current_streak_type") == streak_type
                    and streak_info.get("current_streak_count", 0) >= min_streak_count
                ):
                    filtered_fighters.append(fighter)
            total = len(filtered_fighters)
            start_index = offset or 0
            slice_limit = limit if limit and limit > 0 else None
            if slice_limit is None:
                fighters = filtered_fighters[start_index:]
            else:
                fighters = filtered_fighters[start_index:start_index + slice_limit]
        else:
            count_result = await self._session.execute(count_stmt)
            total = count_result.scalar_one_or_none() or 0

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
                    age=_calculate_age(
                        dob=fighter.dob,
                        reference_date=today_utc,
                    ),
                    is_current_champion=fighter.is_current_champion,
                    is_former_champion=fighter.is_former_champion,
                    was_interim=fighter.was_interim if supports_was_interim else False,
                    current_streak_type=fighter_streaks.get(fighter.id, {}).get(
                        "current_streak_type", "none"
                    )
                    if include_streak
                    else "none",
                    current_streak_count=fighter_streaks.get(fighter.id, {}).get(
                        "current_streak_count", 0
                    )
                    if include_streak
                    else 0,
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

        base_columns = self._fighter_comparison_columns()
        load_columns, supports_was_interim = await self._resolve_fighter_columns(
            base_columns
        )
        fighters_stmt = (
            select(Fighter)
            .options(load_only(*load_columns))
            .where(Fighter.id.in_(ordered_ids))
        )
        fighters_result = await self._session.execute(fighters_stmt)
        fighters = fighters_result.scalars().all()
        fighter_map = {fighter.id: fighter for fighter in fighters}

        today_utc: date = datetime.now(tz=UTC).date()

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
            if category == "fight_history":
                continue
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
                    age=_calculate_age(
                        dob=fighter.dob,
                        reference_date=today_utc,
                    ),
                    is_current_champion=fighter.is_current_champion,
                    is_former_champion=fighter.is_former_champion,
                    was_interim=(
                        fighter.was_interim if supports_was_interim else False
                    ),
                )
            )

        return comparison

    async def count_fighters(self) -> int:
        """Get the total count of fighters in the database."""
        query = select(func.count()).select_from(Fighter)
        result = await self._session.execute(query)
        count = result.scalar_one_or_none()
        return count if count is not None else 0

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
            .where(fighter_stats.c.category != "fight_history")
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
            .where(fighter_stats.c.category != "fight_history")
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
        base_columns = self._fighter_summary_columns()
        load_columns, _ = await self._resolve_fighter_columns(
            base_columns, include_was_interim=False
        )
        query = (
            select(Fighter)
            .options(load_only(*load_columns))
            .order_by(func.random())
            .limit(1)
        )
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
