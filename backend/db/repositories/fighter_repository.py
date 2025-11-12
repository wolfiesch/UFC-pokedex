"""Fighter repository for CRUD operations and fighter-focused queries.

This repository handles:
- Fighter listing with pagination
- Fighter detail retrieval
- Fighter search with multiple filters
- Fighter comparison
- Streak computation (batch and individual)
- Random fighter selection
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Literal, TypeVar
from typing import cast as typing_cast

from sqlalchemy import func, literal, select, true, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from backend.db.models import Event, Fight, Fighter, FighterRanking, fighter_stats
from backend.db.repositories.base import (
    BaseRepository,
    _calculate_age,
    _invert_fight_result,
    _normalize_result_category,
)
from backend.db.repositories.fight_utils import (
    compute_record_from_fights,
    create_fight_key,
    should_replace_fight,
    sort_fight_history,
)
from backend.schemas.fighter import (
    FighterComparisonEntry,
    FighterDetail,
    FighterListItem,
    FightHistoryEntry,
)
from backend.services.image_resolver import (
    resolve_fighter_image,
)

# Type alias for valid streak types
StreakType = Literal["win", "loss", "draw", "none"]

# Generic roster entry used by helper utilities that can operate on
# ``FighterListItem`` instances or richer ``FighterDetail`` records.
RosterEntry = TypeVar("RosterEntry")


@dataclass(frozen=True)
class FighterSearchFilters:
    """Normalized roster search filters shared by multiple repositories."""

    query: str | None
    stance: str | None
    division: str | None
    champion_statuses: tuple[str, ...] | None
    streak_type: StreakType | None
    min_streak_count: int | None


@dataclass
class FighterRankingSummary:
    """Lightweight bundle of ranking metadata for a fighter."""

    current_rank: int | None = None
    current_rank_date: date | None = None
    current_rank_division: str | None = None
    current_rank_source: str | None = None
    peak_rank: int | None = None
    peak_rank_date: date | None = None
    peak_rank_division: str | None = None
    peak_rank_source: str | None = None


def normalize_search_filters(
    *,
    query: str | None,
    stance: str | None,
    division: str | None,
    champion_statuses: Iterable[str] | None,
    streak_type: str | None,
    min_streak_count: int | None,
) -> FighterSearchFilters:
    """Return sanitized search inputs for consistent roster filtering.

    The normalization step trims whitespace, deduplicates champion status flags,
    coerces streak metadata into canonical literals, and ensures streak counts
    are only considered when meaningful.
    """

    normalized_query = (query or "").strip()
    normalized_stance = (stance or "").strip()
    normalized_division = (division or "").strip()

    champion_tuple: tuple[str, ...] | None = None
    if champion_statuses:
        champion_set = {
            status.strip().lower()
            for status in champion_statuses
            if status and status.strip()
        }
        if champion_set:
            champion_tuple = tuple(sorted(champion_set))

    normalized_streak: StreakType | None = None
    if streak_type:
        candidate = streak_type.strip().lower()
        normalized_streak = _validate_streak_type(candidate)
        if normalized_streak not in ("win", "loss"):
            raise ValueError(
                "streak_type must be either 'win' or 'loss' when searching fighters",
            )

    normalized_count = (
        min_streak_count
        if (min_streak_count is not None and min_streak_count > 0)
        else None
    )

    return FighterSearchFilters(
        query=normalized_query or None,
        stance=normalized_stance or None,
        division=normalized_division or None,
        champion_statuses=champion_tuple,
        streak_type=normalized_streak,
        min_streak_count=normalized_count,
    )


def filter_roster_entries(
    roster: Iterable[RosterEntry],
    *,
    filters: FighterSearchFilters,
) -> list[RosterEntry]:
    """Return roster entries that satisfy the provided filters."""

    query_lower = filters.query.lower() if filters.query else None
    stance_lower = filters.stance.lower() if filters.stance else None
    division_lower = filters.division.lower() if filters.division else None

    filtered: list[RosterEntry] = []
    for fighter in roster:
        name_value = getattr(fighter, "name", "") or ""
        nickname_value = getattr(fighter, "nickname", "") or ""
        stance_value = getattr(fighter, "stance", "") or ""
        division_value = getattr(fighter, "division", "") or ""

        matches_query = True
        if query_lower:
            haystack = " ".join(
                part for part in (name_value, nickname_value) if part
            ).lower()
            matches_query = query_lower in haystack

        matches_stance = True
        if stance_lower:
            matches_stance = stance_value.lower() == stance_lower

        matches_division = True
        if division_lower:
            matches_division = division_value.lower() == division_lower

        matches_champion = True
        if filters.champion_statuses:
            status_flags: dict[str, bool] = {
                "current": bool(getattr(fighter, "is_current_champion", False)),
                "former": bool(getattr(fighter, "is_former_champion", False)),
                "interim": bool(getattr(fighter, "was_interim", False)),
            }
            matches_champion = any(
                status_flags.get(status, False) for status in filters.champion_statuses
            )

        matches_streak = True
        if filters.streak_type and filters.min_streak_count is not None:
            streak_type = getattr(fighter, "current_streak_type", "none") or "none"
            streak_count = int(getattr(fighter, "current_streak_count", 0) or 0)
            matches_streak = (
                streak_type == filters.streak_type
                and streak_count >= filters.min_streak_count
            )

        if (
            matches_query
            and matches_stance
            and matches_division
            and matches_champion
            and matches_streak
        ):
            filtered.append(fighter)

    return filtered


def paginate_roster_entries(
    roster: Iterable[RosterEntry],
    *,
    limit: int | None,
    offset: int | None,
) -> list[RosterEntry]:
    """Apply simple limit/offset pagination to roster data sets."""

    entries = list(roster)
    start_index = offset if (offset is not None and offset >= 0) else 0
    if limit is None or limit <= 0:
        return entries[start_index:]
    return entries[start_index : start_index + limit]


# Initialize logger
logger = logging.getLogger(__name__)

_DEFAULT_RANKING_SOURCE = (
    os.getenv("FIGHTER_RANKING_SOURCE")
    or os.getenv("DEFAULT_RANKING_SOURCE")
    or "fightmatrix"
)
_DEFAULT_RANKING_SOURCE = (_DEFAULT_RANKING_SOURCE or "").strip() or None


def _validate_streak_type(value: str | None) -> StreakType | None:
    """Validate streak type matches allowed values.

    Args:
        value: The streak type value to validate

    Returns:
        The validated streak type or None

    Raises:
        ValueError: If the value is not a valid streak type
    """
    if value is None:
        return None
    if value not in ("win", "loss", "draw", "none"):
        raise ValueError(f"Invalid streak type: {value}")
    return value  # type: ignore[return-value]  # We've validated it matches the literal


class FighterRepository(BaseRepository):
    """Repository for fighter CRUD operations and queries."""

    def _fighter_summary_columns(self) -> list[Any]:
        """Columns to load for fighter list/summary views."""
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
            Fighter.current_streak_type,
            Fighter.current_streak_count,
            Fighter.last_fight_date,
            Fighter.birthplace,
            Fighter.birthplace_city,
            Fighter.birthplace_country,
            Fighter.nationality,
            Fighter.fighting_out_of,
            Fighter.training_gym,
            Fighter.training_city,
            Fighter.training_country,
        ]

    def _fighter_detail_columns(self) -> list[Any]:
        """Columns to load for detailed fighter views."""
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
            Fighter.birthplace,
            Fighter.birthplace_city,
            Fighter.birthplace_country,
            Fighter.nationality,
            Fighter.fighting_out_of,
            Fighter.training_gym,
            Fighter.training_city,
            Fighter.training_country,
        ]

    def _fighter_comparison_columns(self) -> list[Any]:
        """Columns to load for fighter comparison views."""
        return [
            Fighter.id,
            Fighter.name,
            Fighter.record,
            Fighter.division,
            Fighter.image_url,
            Fighter.is_current_champion,
            Fighter.is_former_champion,
        ]

    def _ranking_source(self) -> str | None:
        """Return the preferred ranking source for roster adornments."""

        return _DEFAULT_RANKING_SOURCE

    def _normalize_fight_result(
        self, result: str | None
    ) -> Literal["win", "loss", "draw", "nc"] | None:
        """Normalize fight result to canonical form (reuses favorites_service pattern)."""
        if result is None:
            return None
        normalized = result.strip().lower()
        if normalized in {"w", "win"}:
            return "win"
        if normalized in {"l", "loss"}:
            return "loss"
        if normalized.startswith("draw"):
            return "draw"
        if normalized in {"nc", "no contest"}:
            return "nc"
        return None  # Ignore "next" and other values

    async def _fetch_ranking_summaries(
        self, fighter_ids: Sequence[str]
    ) -> dict[str, FighterRankingSummary]:
        """Lookup current and peak rankings for the provided fighters."""

        ranking_source = self._ranking_source()
        if not ranking_source:
            return {}

        deduped_ids = [fid for fid in dict.fromkeys(fighter_ids) if fid]
        if not deduped_ids:
            return {}

        # Latest ranking snapshot per fighter for the configured source.
        current_subquery = (
            select(
                FighterRanking.fighter_id.label("fighter_id"),
                FighterRanking.rank.label("rank"),
                FighterRanking.rank_date.label("rank_date"),
                FighterRanking.division.label("division"),
                FighterRanking.source.label("source"),
                func.row_number()
                .over(
                    partition_by=FighterRanking.fighter_id,
                    order_by=FighterRanking.rank_date.desc(),
                )
                .label("row_number"),
            )
            .where(FighterRanking.fighter_id.in_(deduped_ids))
            .where(FighterRanking.source == ranking_source)
        ).subquery()

        current_rows = await self._session.execute(
            select(
                current_subquery.c.fighter_id,
                current_subquery.c.rank,
                current_subquery.c.rank_date,
                current_subquery.c.division,
                current_subquery.c.source,
            ).where(current_subquery.c.row_number == 1)
        )

        # Best (lowest numeric) rank ever achieved for the configured source.
        peak_subquery = (
            select(
                FighterRanking.fighter_id.label("fighter_id"),
                FighterRanking.rank.label("rank"),
                FighterRanking.rank_date.label("rank_date"),
                FighterRanking.division.label("division"),
                FighterRanking.source.label("source"),
                func.row_number()
                .over(
                    partition_by=FighterRanking.fighter_id,
                    order_by=(
                        FighterRanking.rank.asc(),
                        FighterRanking.rank_date.desc(),
                    ),
                )
                .label("row_number"),
            )
            .where(FighterRanking.fighter_id.in_(deduped_ids))
            .where(FighterRanking.source == ranking_source)
            .where(FighterRanking.rank.isnot(None))
        ).subquery()

        peak_rows = await self._session.execute(
            select(
                peak_subquery.c.fighter_id,
                peak_subquery.c.rank,
                peak_subquery.c.rank_date,
                peak_subquery.c.division,
                peak_subquery.c.source,
            ).where(peak_subquery.c.row_number == 1)
        )

        summaries: dict[str, FighterRankingSummary] = {}

        for row in current_rows:
            summary = summaries.setdefault(row.fighter_id, FighterRankingSummary())
            summary.current_rank = row.rank
            summary.current_rank_date = row.rank_date
            summary.current_rank_division = row.division
            summary.current_rank_source = row.source

        for row in peak_rows:
            summary = summaries.setdefault(row.fighter_id, FighterRankingSummary())
            summary.peak_rank = row.rank
            summary.peak_rank_date = row.rank_date
            summary.peak_rank_division = row.division
            summary.peak_rank_source = row.source

        return summaries

    async def _fetch_fight_status(
        self, fighter_ids: Sequence[str]
    ) -> dict[str, dict[str, date | Literal["win", "loss", "draw", "nc"] | None]]:
        """Fetch upcoming fight dates and last fight results for given fighters.

        Returns a dict mapping fighter_id to a dict with:
        - next_fight_date: date of next upcoming fight (or None)
        - last_fight_result: normalized result of last fight (or None)
        """
        if not fighter_ids:
            return {}

        # Subquery: Get next upcoming fight date for each fighter
        # Upcoming fights have result='next' and event_date > today
        next_fight_subq = (
            select(
                Fight.fighter_id.label("fighter_id"),
                func.min(Fight.event_date).label("next_fight_date"),
            )
            .join(Event, Fight.event_id == Event.id)
            .where(Fight.fighter_id.in_(fighter_ids))
            .where(Event.date > func.current_date())
            .where(Fight.result == "next")
            .group_by(Fight.fighter_id)
        ).subquery()

        # Subquery: Get last fight result for fighters with last_fight_date
        # Match fights where event_date equals the fighter's last_fight_date
        # Order by: prioritize valid results (W/L/win/loss) over N/A or other values
        last_fight_subq = (
            select(
                Fight.fighter_id.label("fighter_id"),
                Fight.result.label("last_result"),
                func.row_number()
                .over(
                    partition_by=Fight.fighter_id,
                    order_by=(
                        # Prioritize rows with valid results (W, L, win, loss, draw, NC)
                        func.case(
                            (Fight.result.in_(["W", "L", "win", "loss", "draw", "nc", "NC", "no contest"]), 0),
                            else_=1
                        ),
                        Fight.event_date.desc(),
                    ),
                )
                .label("row_number"),
            )
            .join(Fighter, Fight.fighter_id == Fighter.id)
            .where(Fight.fighter_id.in_(fighter_ids))
            .where(Fight.event_date == Fighter.last_fight_date)
        ).subquery()

        # Execute both queries
        next_fight_rows = await self._session.execute(
            select(
                next_fight_subq.c.fighter_id,
                next_fight_subq.c.next_fight_date,
            )
        )

        last_fight_rows = await self._session.execute(
            select(
                last_fight_subq.c.fighter_id,
                last_fight_subq.c.last_result,
            ).where(last_fight_subq.c.row_number == 1)
        )

        # Build result dict
        status_by_fighter: dict[
            str, dict[str, date | Literal["win", "loss", "draw", "nc"] | None]
        ] = {}

        for row in next_fight_rows:
            status = status_by_fighter.setdefault(row.fighter_id, {})
            status["next_fight_date"] = row.next_fight_date

        for row in last_fight_rows:
            status = status_by_fighter.setdefault(row.fighter_id, {})
            status["last_fight_result"] = self._normalize_fight_result(row.last_result)

        return status_by_fighter

    async def list_fighters(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        nationality: str | None = None,
        birthplace_country: str | None = None,
        birthplace_city: str | None = None,
        training_country: str | None = None,
        training_city: str | None = None,
        training_gym: str | None = None,
        has_location_data: bool | None = None,
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
            .order_by(Fighter.last_fight_date.desc().nulls_last(), Fighter.name, Fighter.id)
        )

        # Apply location filters
        if nationality:
            logger.debug(f"Applying nationality filter: {nationality}")
            query = query.where(Fighter.nationality == nationality)
        if birthplace_country:
            query = query.where(Fighter.birthplace_country == birthplace_country)
        if birthplace_city:
            query = query.where(Fighter.birthplace_city == birthplace_city)
        if training_country:
            query = query.where(Fighter.training_country == training_country)
        if training_city:
            query = query.where(Fighter.training_city == training_city)
        if training_gym:
            # Partial match for gym name
            query = query.where(Fighter.training_gym.ilike(f"%{training_gym}%"))
        if has_location_data is not None:
            from sqlalchemy import or_

            if has_location_data:
                query = query.where(
                    or_(
                        Fighter.birthplace.isnot(None),
                        Fighter.training_gym.isnot(None),
                    )
                )
            else:
                query = query.where(
                    Fighter.birthplace.is_(None),
                    Fighter.training_gym.is_(None),
                )

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        result = await self._session.execute(query)
        fighters = result.scalars().all()
        fighter_ids = [f.id for f in fighters]

        # Optionally compute current streaks for the returned fighters only
        streak_by_fighter: dict[
            str, dict[str, int | Literal["win", "loss", "draw", "none"]]
        ] = {}
        if include_streak and fighters:
            streak_by_fighter = await self._batch_compute_streaks(
                fighter_ids, window=streak_window
            )

        # Fetch fight status (upcoming and last fight result) for all fighters
        fight_status_by_fighter: dict[
            str, dict[str, date | Literal["win", "loss", "draw", "nc"] | None]
        ] = {}
        if fighters:
            fight_status_by_fighter = await self._fetch_fight_status(fighter_ids)

        ranking_summaries = (
            await self._fetch_ranking_summaries(fighter_ids) if fighters else {}
        )

        # Cache a single "today" value in UTC so every fighter on the page uses
        # the same reference point for age calculations.
        today_utc: date = datetime.now(tz=UTC).date()

        roster_entries: list[FighterListItem] = []
        for fighter in fighters:
            streak_bundle = streak_by_fighter.get(fighter.id, {})
            fight_status = fight_status_by_fighter.get(fighter.id, {})
            ranking = ranking_summaries.get(fighter.id)
            roster_entries.append(
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
                            streak_bundle.get("current_streak_type", "none")
                            if include_streak
                            else "none"
                        ),
                    ),
                    current_streak_count=(
                        int(streak_bundle.get("current_streak_count", 0))
                        if include_streak
                        else 0
                    ),
                    current_rank=ranking.current_rank if ranking else None,
                    current_rank_date=ranking.current_rank_date if ranking else None,
                    current_rank_division=ranking.current_rank_division
                    if ranking
                    else None,
                    current_rank_source=ranking.current_rank_source if ranking else None,
                    peak_rank=ranking.peak_rank if ranking else None,
                    peak_rank_date=ranking.peak_rank_date if ranking else None,
                    peak_rank_division=ranking.peak_rank_division if ranking else None,
                    peak_rank_source=ranking.peak_rank_source if ranking else None,
                    birthplace=fighter.birthplace,
                    birthplace_city=fighter.birthplace_city,
                    birthplace_country=fighter.birthplace_country,
                    nationality=fighter.nationality,
                    fighting_out_of=fighter.fighting_out_of,
                    training_gym=fighter.training_gym,
                    training_city=fighter.training_city,
                    training_country=fighter.training_country,
                    next_fight_date=typing_cast(
                        date | None, fight_status.get("next_fight_date")
                    ),
                    last_fight_date=fighter.last_fight_date,
                    last_fight_result=typing_cast(
                        Literal["win", "loss", "draw", "nc"] | None,
                        fight_status.get("last_fight_result"),
                    ),
                )
            )
        return roster_entries

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Get detailed fighter information by ID with optimized single-query fetch.

        Performance optimization: Uses a single CTE UNION query to fetch all fights
        (both as primary fighter and opponent) with opponent names in one database round trip.
        """
        import time

        start_time = time.time()

        # Get fighter basic info
        base_columns = self._fighter_detail_columns()
        load_columns, supports_was_interim = await self._resolve_fighter_columns(
            base_columns
        )
        fighter_query = (
            select(Fighter)
            .options(load_only(*load_columns))
            .where(Fighter.id == fighter_id)
        )
        fighter_result = await self._session.execute(fighter_query)
        fighter = fighter_result.scalar_one_or_none()

        if fighter is None:
            return None

        # Fighter stats from fighter_stats table
        # NOTE: The fighter_stats table exists but is not populated by the scraper.
        # Stats fields (striking, grappling, etc.) will be empty until scraper is updated.
        stats_map: dict[str, dict[str, str]] = {}

        # OPTIMIZED: Single query to get ALL fights (primary + opponent) with opponent names
        # Uses CTE (Common Table Expression) with UNION to combine results

        # CTE 1: Primary fights (where fighter is fighter_id)
        primary_fights_cte = (
            select(
                Fight.id.label("fight_id"),
                Fight.event_name,
                Fight.event_date,
                Fight.opponent_id,
                Fight.opponent_name,
                Fight.result,
                Fight.method,
                Fight.round,
                Fight.time,
                Fight.fight_card_url,
                Fight.stats,
                literal(True).label("is_primary"),  # Mark as primary fight
                literal(None).label("inverted_opponent_id"),  # Placeholder
            ).where(Fight.fighter_id == fighter_id)
        ).cte("primary_fights")

        # CTE 2: Opponent fights (where fighter is opponent_id) with opponent names via JOIN
        opponent_fights_cte = (
            select(
                Fight.id.label("fight_id"),
                Fight.event_name,
                Fight.event_date,
                literal(None).label(
                    "opponent_id"
                ),  # Will use inverted_opponent_id instead
                literal(None).label("opponent_name"),  # Will fetch from JOIN
                Fight.result,
                Fight.method,
                Fight.round,
                Fight.time,
                Fight.fight_card_url,
                Fight.stats,
                literal(False).label("is_primary"),  # Mark as opponent fight
                Fight.fighter_id.label("inverted_opponent_id"),  # Fighter is opponent
            ).where(Fight.opponent_id == fighter_id)
        ).cte("opponent_fights")

        # UNION ALL: Combine both CTEs
        combined_query = select(primary_fights_cte).union_all(
            select(opponent_fights_cte)
        )

        # Execute single query to get all fights
        all_fights_result = await self._session.execute(combined_query)
        all_fights_rows = all_fights_result.all()

        # Collect unique opponent IDs for name lookup (single query)
        opponent_ids: set[str] = set()
        for row in all_fights_rows:
            if row.is_primary and row.opponent_id:
                opponent_ids.add(row.opponent_id)
            elif not row.is_primary and row.inverted_opponent_id:
                opponent_ids.add(row.inverted_opponent_id)

        # Single query to get all opponent names
        opponent_lookup: dict[str, str] = {}
        if opponent_ids:
            opponent_rows = await self._session.execute(
                select(Fighter.id, Fighter.name).where(Fighter.id.in_(opponent_ids))
            )
            opponent_lookup = {row.id: row.name for row in opponent_rows.all()}

        # Build fight history, deduplicating by fight metadata (not database ID)
        # This prevents duplicate entries when both fighters have Fight records for the same bout
        # Prioritize fights where fighter_id matches (fighter's own perspective)
        # Also prioritize fights with actual results (win/loss/draw) over "N/A"
        fight_dict: dict[tuple[str, str | None, str], FightHistoryEntry] = {}

        # Process all fights
        for row in all_fights_rows:
            if row.is_primary:
                # Primary fight (fighter is fighter_id)
                opponent_name = row.opponent_name or opponent_lookup.get(
                    row.opponent_id, "Unknown"
                )
                fight_key = create_fight_key(
                    row.event_name,
                    row.event_date,
                    row.opponent_id,
                    opponent_name,
                )

                new_entry = FightHistoryEntry(
                    fight_id=row.fight_id,
                    event_name=row.event_name,
                    event_date=row.event_date,
                    opponent=opponent_name,
                    opponent_id=row.opponent_id,
                    result=row.result,
                    method=row.method or "",
                    round=row.round,
                    time=row.time,
                    fight_card_url=row.fight_card_url,
                    stats=row.stats,
                )

                if fight_key not in fight_dict:
                    fight_dict[fight_key] = new_entry
                elif should_replace_fight(fight_dict[fight_key].result, row.result):
                    # Replace with better result
                    fight_dict[fight_key] = new_entry
            else:
                # Opponent fight (fighter is opponent_id) - invert result
                opponent_id = row.inverted_opponent_id
                opponent_name = opponent_lookup.get(opponent_id, "Unknown")

                fight_key = create_fight_key(
                    row.event_name, row.event_date, opponent_id, opponent_name
                )

                # Invert the result
                inverted_result = _invert_fight_result(row.result)

                new_entry = FightHistoryEntry(
                    fight_id=row.fight_id,
                    event_name=row.event_name,
                    event_date=row.event_date,
                    opponent=opponent_name,
                    opponent_id=opponent_id,
                    result=inverted_result,
                    method=row.method or "",
                    round=row.round,
                    time=row.time,
                    fight_card_url=row.fight_card_url,
                    stats=row.stats,
                )

                if fight_key not in fight_dict:
                    fight_dict[fight_key] = new_entry
                elif should_replace_fight(
                    fight_dict[fight_key].result, inverted_result
                ):
                    # Replace with better result
                    fight_dict[fight_key] = new_entry

        # Convert dict to list and sort
        fight_history: list[FightHistoryEntry] = list(fight_dict.values())
        fight_history = sort_fight_history(fight_history)

        # Log query performance
        query_time = time.time() - start_time
        if query_time > 0.1:  # Log slow queries (>100ms)
            logger.warning(f"Slow fighter query: {fighter_id} took {query_time:.3f}s")

        # Compute record from fight_history if not already populated
        computed_record = fighter.record
        if not computed_record:
            computed_from_fights = compute_record_from_fights(fight_history)
            if computed_from_fights:
                computed_record = computed_from_fights

        today_utc: date = datetime.now(tz=UTC).date()
        fighter_age: int | None = _calculate_age(
            dob=fighter.dob,
            reference_date=today_utc,
        )

        summary = (await self._fetch_ranking_summaries([fighter.id])).get(fighter.id)

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
            current_rank=summary.current_rank if summary else None,
            current_rank_date=summary.current_rank_date if summary else None,
            current_rank_division=summary.current_rank_division if summary else None,
            current_rank_source=summary.current_rank_source if summary else None,
            peak_rank=summary.peak_rank if summary else None,
            peak_rank_date=summary.peak_rank_date if summary else None,
            peak_rank_division=summary.peak_rank_division if summary else None,
            peak_rank_source=summary.peak_rank_source if summary else None,
            birthplace=fighter.birthplace,
            birthplace_city=fighter.birthplace_city,
            birthplace_country=fighter.birthplace_country,
            nationality=fighter.nationality,
            fighting_out_of=fighter.fighting_out_of,
            training_gym=fighter.training_gym,
            training_city=fighter.training_city,
            training_country=fighter.training_country,
        )

    async def search_fighters(
        self,
        query: str | None = None,
        stance: str | None = None,
        division: str | None = None,
        champion_statuses: list[str] | None = None,
        streak_type: str | None = None,
        min_streak_count: int | None = None,
        include_locations: bool = True,
        include_streak: bool = False,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[list[FighterListItem], int]:
        """Search fighters by name, stance, division, champion status, or streak.

        Supports pagination with limit and offset parameters.
        """

        filters = []
        normalized_filters = normalize_search_filters(
            query=query,
            stance=stance,
            division=division,
            champion_statuses=champion_statuses,
            streak_type=streak_type,
            min_streak_count=min_streak_count,
        )

        if normalized_filters.query:
            # Use ILIKE for case-insensitive search
            # This works with PostgreSQL trigram indexes (pg_trgm) for 10x speedup
            # Falls back to standard LIKE behavior in SQLite
            pattern = f"%{normalized_filters.query}%"

            # Base search conditions (name and nickname)
            search_conditions = [
                Fighter.name.ilike(pattern),
                Fighter.nickname.ilike(pattern),
            ]

            # Add location search if enabled
            if include_locations:
                search_conditions.extend(
                    [
                        Fighter.birthplace.ilike(pattern),
                        Fighter.birthplace_city.ilike(pattern),
                        Fighter.birthplace_country.ilike(pattern),
                        Fighter.nationality.ilike(pattern),
                        Fighter.training_gym.ilike(pattern),
                        Fighter.training_city.ilike(pattern),
                        Fighter.training_country.ilike(pattern),
                    ]
                )

            from sqlalchemy import or_

            filters.append(or_(*search_conditions))
        if normalized_filters.stance:
            filters.append(Fighter.stance == normalized_filters.stance)
        if normalized_filters.division:
            filters.append(Fighter.division == normalized_filters.division)

        if normalized_filters.champion_statuses:
            supports_was_interim = await self._supports_was_interim()
            # Build OR conditions for multiple champion statuses
            champion_conditions = []
            for status in normalized_filters.champion_statuses:
                if status == "current":
                    champion_conditions.append(Fighter.is_current_champion.is_(True))
                elif status == "former":
                    champion_conditions.append(Fighter.is_former_champion.is_(True))
                elif status == "interim" and supports_was_interim:
                    champion_conditions.append(Fighter.was_interim.is_(True))
            if champion_conditions:
                # Use OR to combine conditions (show fighters matching ANY status)
                from sqlalchemy import or_

                filters.append(or_(*champion_conditions))

        # Streak filtering using pre-computed columns (Phase 2 optimization)
        if (
            normalized_filters.streak_type
            and normalized_filters.min_streak_count is not None
        ):
            filters.append(
                Fighter.current_streak_type == normalized_filters.streak_type
            )
            filters.append(
                Fighter.current_streak_count >= normalized_filters.min_streak_count
            )

        base_columns = self._fighter_summary_columns()
        load_columns, supports_was_interim = await self._resolve_fighter_columns(
            base_columns
        )
        stmt = select(Fighter).options(load_only(*load_columns)).order_by(Fighter.last_fight_date.desc().nulls_last(), Fighter.name)
        count_stmt = select(func.count()).select_from(Fighter)

        for condition in filters:
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        # Apply pagination (now works for ALL filters including streaks!)
        if offset is not None and offset > 0:
            stmt = stmt.offset(offset)
        if limit is not None and limit > 0:
            stmt = stmt.limit(limit)

        # Get total count
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one_or_none() or 0

        # Execute query
        result = await self._session.execute(stmt)
        fighters = result.scalars().all()
        fighter_ids = [f.id for f in fighters]
        ranking_summaries = (
            await self._fetch_ranking_summaries(fighter_ids) if fighter_ids else {}
        )

        # Fetch fight status (upcoming and last fight result) for all fighters
        fight_status_by_fighter: dict[
            str, dict[str, date | Literal["win", "loss", "draw", "nc"] | None]
        ] = {}
        if fighter_ids:
            fight_status_by_fighter = await self._fetch_fight_status(fighter_ids)

        # Use a single "today" snapshot so every returned card displays the same
        # age even if the request straddles midnight in UTC.
        today_utc: date = datetime.now(tz=UTC).date()

        # Phase 2: Streak data now comes from pre-computed database columns
        # No need to compute streaks - they're already in the Fighter model!

        roster_entries: list[FighterListItem] = []
        for fighter in fighters:
            fight_status = fight_status_by_fighter.get(fighter.id, {})
            ranking = ranking_summaries.get(fighter.id)
            roster_entries.append(
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
                    current_streak_type=(
                        (_validate_streak_type(fighter.current_streak_type) or "none")
                        if include_streak
                        else "none"
                    ),
                    current_streak_count=(
                        fighter.current_streak_count if include_streak else 0
                    ),
                    current_rank=ranking.current_rank if ranking else None,
                    current_rank_date=ranking.current_rank_date if ranking else None,
                    current_rank_division=ranking.current_rank_division
                    if ranking
                    else None,
                    current_rank_source=ranking.current_rank_source if ranking else None,
                    peak_rank=ranking.peak_rank if ranking else None,
                    peak_rank_date=ranking.peak_rank_date if ranking else None,
                    peak_rank_division=ranking.peak_rank_division if ranking else None,
                    peak_rank_source=ranking.peak_rank_source if ranking else None,
                    birthplace=fighter.birthplace,
                    birthplace_city=fighter.birthplace_city,
                    birthplace_country=fighter.birthplace_country,
                    nationality=fighter.nationality,
                    fighting_out_of=fighter.fighting_out_of,
                    training_gym=fighter.training_gym,
                    training_city=fighter.training_city,
                    training_country=fighter.training_country,
                    next_fight_date=typing_cast(
                        date | None, fight_status.get("next_fight_date")
                    ),
                    last_fight_date=fighter.last_fight_date,
                    last_fight_result=typing_cast(
                        Literal["win", "loss", "draw", "nc"] | None,
                        fight_status.get("last_fight_result"),
                    ),
                )
            )

        return (roster_entries, total)

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

    async def count_fighters(
        self,
        nationality: str | None = None,
        birthplace_country: str | None = None,
        birthplace_city: str | None = None,
        training_country: str | None = None,
        training_city: str | None = None,
        training_gym: str | None = None,
        has_location_data: bool | None = None,
    ) -> int:
        """Get the total count of fighters in the database with optional filters."""
        query = select(func.count()).select_from(Fighter)

        # Apply location filters
        if nationality:
            logger.debug(f"Applying nationality filter for count: {nationality}")
            query = query.where(Fighter.nationality == nationality)
        if birthplace_country:
            query = query.where(Fighter.birthplace_country == birthplace_country)
        if birthplace_city:
            query = query.where(Fighter.birthplace_city == birthplace_city)
        if training_country:
            query = query.where(Fighter.training_country == training_country)
        if training_city:
            query = query.where(Fighter.training_city == training_city)
        if training_gym:
            query = query.where(Fighter.training_gym.ilike(f"%{training_gym}%"))
        if has_location_data is not None:
            from sqlalchemy import or_

            if has_location_data:
                query = query.where(
                    or_(
                        Fighter.birthplace.isnot(None),
                        Fighter.training_gym.isnot(None),
                    )
                )
            else:
                query = query.where(
                    Fighter.birthplace.is_(None),
                    Fighter.training_gym.is_(None),
                )

        result = await self._session.execute(query)
        count = result.scalar_one_or_none()
        return count if count is not None else 0

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

        ranking = (await self._fetch_ranking_summaries([fighter.id])).get(fighter.id)

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
            current_rank=ranking.current_rank if ranking else None,
            current_rank_date=ranking.current_rank_date if ranking else None,
            current_rank_division=ranking.current_rank_division if ranking else None,
            current_rank_source=ranking.current_rank_source if ranking else None,
            peak_rank=ranking.peak_rank if ranking else None,
            peak_rank_date=ranking.peak_rank_date if ranking else None,
            peak_rank_division=ranking.peak_rank_division if ranking else None,
            peak_rank_source=ranking.peak_rank_source if ranking else None,
            birthplace=fighter.birthplace,
            birthplace_city=fighter.birthplace_city,
            birthplace_country=fighter.birthplace_country,
            nationality=fighter.nationality,
            fighting_out_of=fighter.fighting_out_of,
            training_gym=fighter.training_gym,
            training_city=fighter.training_city,
            training_country=fighter.training_country,
        )

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

        unique_fighter_ids = list(dict.fromkeys(fighter_ids))
        if not unique_fighter_ids:
            return {}
        fighter_ids = unique_fighter_ids

        effective_window: int | None = None if window is None else max(2, window)

        # Inline table of fighter IDs so we can join laterals efficiently.
        fighter_id_selects = [
            select(literal(f_id).label("fighter_id")) for f_id in unique_fighter_ids
        ]
        if len(fighter_id_selects) == 1:
            target_fighters = fighter_id_selects[0].cte("target_fighters")
        else:
            target_fighters = union_all(*fighter_id_selects).cte("target_fighters")

        order_clause = Fight.event_date.desc().nulls_last()

        # Remove individual limits - we'll limit after union
        primary_fights = (
            select(
                Fight.event_date.label("event_date"),
                Fight.result.label("result"),
            )
            .where(Fight.fighter_id == target_fighters.c.fighter_id)
            .order_by(order_clause)
        )
        primary_fights = primary_fights.lateral("primary_fights")

        opponent_fights = (
            select(
                Fight.event_date.label("event_date"),
                Fight.result.label("result"),
            )
            .where(Fight.opponent_id == target_fighters.c.fighter_id)
            .order_by(order_clause)
        )
        opponent_fights = opponent_fights.lateral("opponent_fights")

        primary_stmt = select(
            target_fighters.c.fighter_id.label("subject_id"),
            primary_fights.c.event_date,
            primary_fights.c.result,
            literal(True).label("is_primary"),
        ).select_from(target_fighters.join(primary_fights, true()))

        opponent_stmt = select(
            target_fighters.c.fighter_id.label("subject_id"),
            opponent_fights.c.event_date,
            opponent_fights.c.result,
            literal(False).label("is_primary"),
        ).select_from(target_fighters.join(opponent_fights, true()))

        combined = union_all(primary_stmt, opponent_stmt).subquery("subject_fights")

        # Apply window limit to total combined fights per fighter
        if effective_window is not None:
            # Use window function to limit total fights per fighter
            stmt = select(
                combined.c.subject_id,
                combined.c.event_date,
                combined.c.result,
                combined.c.is_primary,
                func.row_number()
                .over(
                    partition_by=combined.c.subject_id,
                    order_by=combined.c.event_date.desc().nulls_last(),
                )
                .label("row_num"),
            ).order_by(combined.c.subject_id, combined.c.event_date.desc().nulls_last())
            # Filter to only the first N fights per fighter
            stmt = select(
                stmt.c.subject_id,
                stmt.c.event_date,
                stmt.c.result,
                stmt.c.is_primary,
            ).where(stmt.c.row_num <= effective_window)
        else:
            stmt = select(
                combined.c.subject_id,
                combined.c.event_date,
                combined.c.result,
                combined.c.is_primary,
            ).order_by(combined.c.subject_id, combined.c.event_date.desc().nulls_last())

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
                last_completed = typing_cast(Literal["win", "loss", "draw"], category)
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
        return result.get(
            fighter_id, {"current_streak_type": "none", "current_streak_count": 0}
        )

    async def update_fighter_location(
        self,
        fighter_id: str,
        *,
        birthplace: str | None = None,
        birthplace_city: str | None = None,
        birthplace_country: str | None = None,
        nationality: str | None = None,
        training_gym: str | None = None,
        training_city: str | None = None,
        training_country: str | None = None,
        ufc_com_slug: str | None = None,
        ufc_com_match_confidence: float | None = None,
        ufc_com_match_method: str | None = None,
        ufc_com_scraped_at: datetime | None = None,
        needs_manual_review: bool | None = None,
    ) -> None:
        """Update fighter location and UFC.com metadata fields.

        Args:
            fighter_id: UFCStats fighter ID
            birthplace: Full birthplace string (e.g., "Dublin, Ireland")
            birthplace_city: Extracted city (e.g., "Dublin")
            birthplace_country: Extracted country (e.g., "Ireland")
            nationality: Nationality from Sherdog (e.g., "Irish")
            training_gym: Gym name (e.g., "SBG Ireland")
            training_city: Training city (from gym lookup)
            training_country: Training country (from gym lookup)
            ufc_com_slug: UFC.com athlete slug
            ufc_com_match_confidence: Match confidence score (0-100)
            ufc_com_match_method: Match method ('auto_high', 'auto_medium', 'manual', 'verified')
            ufc_com_scraped_at: Timestamp of UFC.com data fetch
            needs_manual_review: Flag for manual verification
        """
        from sqlalchemy import update

        stmt = (
            update(Fighter)
            .where(Fighter.id == fighter_id)
            .values(
                birthplace=birthplace,
                birthplace_city=birthplace_city,
                birthplace_country=birthplace_country,
                nationality=nationality,
                training_gym=training_gym,
                training_city=training_city,
                training_country=training_country,
                ufc_com_slug=ufc_com_slug,
                ufc_com_match_confidence=ufc_com_match_confidence,
                ufc_com_match_method=ufc_com_match_method,
                ufc_com_scraped_at=ufc_com_scraped_at,
                **(
                    {"needs_manual_review": needs_manual_review}
                    if needs_manual_review is not None
                    else {}
                ),
            )
        )
        await self._session.execute(stmt)

    async def update_fighter_nationality(
        self,
        fighter_id: str,
        nationality: str,
    ) -> None:
        """Update fighter nationality from Sherdog data.

        Args:
            fighter_id: UFCStats fighter ID
            nationality: Nationality string (e.g., "Irish", "Brazilian")
        """
        from sqlalchemy import update

        stmt = (
            update(Fighter)
            .where(Fighter.id == fighter_id)
            .values(nationality=nationality)
        )
        await self._session.execute(stmt)

    async def get_fighters_without_ufc_com_data(self) -> Sequence[Fighter]:
        """Get fighters without UFC.com data (for Sherdog nationality loading).

        Returns:
            List of Fighter objects where ufc_com_slug is NULL
        """
        stmt = select(Fighter).where(Fighter.ufc_com_slug.is_(None))
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_country_stats(
        self, group_by: str
    ) -> tuple[list[dict[str, Any]], int]:
        """Get fighter count by country.

        Args:
            group_by: Field to group by ('birthplace', 'training', or 'nationality')

        Returns:
            Tuple of (list of country stats, total fighters)
        """
        # Determine which column to use
        if group_by == "birthplace":
            column = Fighter.birthplace_country
        elif group_by == "training":
            column = Fighter.training_country
        elif group_by == "nationality":
            column = Fighter.nationality
        else:
            raise ValueError(f"Invalid group_by value: {group_by}")

        # Query for country counts
        query = (
            select(column.label("country"), func.count().label("count"))
            .where(column.isnot(None))
            .group_by(column)
            .order_by(func.count().desc())
        )

        result = await self._session.execute(query)
        rows = result.all()

        # Get total roster count for percentage calculations
        roster_total_query = select(func.count()).select_from(Fighter)
        roster_total_result = await self._session.execute(roster_total_query)
        total = roster_total_result.scalar_one_or_none() or 0

        # Format results with percentage
        stats = []
        for row in rows:
            percentage = round((row.count / total * 100), 1) if total > 0 else 0.0
            stats.append(
                {"country": row.country, "count": row.count, "percentage": percentage}
            )

        return stats, total

    async def get_city_stats(
        self, group_by: str, country: str | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        """Get fighter count by city.

        Args:
            group_by: Field to group by ('birthplace' or 'training')
            country: Optional country filter

        Returns:
            Tuple of (list of city stats, total fighters)
        """
        # Determine which columns to use
        if group_by == "birthplace":
            city_column = Fighter.birthplace_city
            country_column = Fighter.birthplace_country
        elif group_by == "training":
            city_column = Fighter.training_city
            country_column = Fighter.training_country
        else:
            raise ValueError(f"Invalid group_by value: {group_by}")

        # Query for city counts
        query = (
            select(
                city_column.label("city"),
                country_column.label("country"),
                func.count().label("count"),
            )
            .where(city_column.isnot(None))
            .group_by(city_column, country_column)
            .order_by(func.count().desc())
        )

        # Apply country filter if specified
        if country:
            query = query.where(country_column == country)

        result = await self._session.execute(query)
        rows = result.all()

        # Get total roster count (global denominator for percentages)
        roster_total_query = select(func.count()).select_from(Fighter)
        roster_total_result = await self._session.execute(roster_total_query)
        total = roster_total_result.scalar_one_or_none() or 0

        # Format results with percentage
        stats = []
        for row in rows:
            percentage = round((row.count / total * 100), 1) if total > 0 else 0.0
            stats.append(
                {
                    "city": row.city,
                    "country": row.country,
                    "count": row.count,
                    "percentage": percentage,
                }
            )

        return stats, total

    async def get_gym_stats(
        self, country: str | None = None
    ) -> list[dict[str, Any]]:
        """Get fighter count by gym.

        Args:
            country: Optional country filter

        Returns:
            List of gym stats with fighter counts and notable fighters
        """
        # Query for gym counts
        query = (
            select(
                Fighter.training_gym.label("gym"),
                Fighter.training_city.label("city"),
                Fighter.training_country.label("country"),
                func.count().label("fighter_count"),
            )
            .where(Fighter.training_gym.isnot(None))
            .group_by(
                Fighter.training_gym, Fighter.training_city, Fighter.training_country
            )
            .order_by(func.count().desc())
        )

        # Apply country filter if specified
        if country:
            query = query.where(Fighter.training_country == country)

        result = await self._session.execute(query)
        rows = result.all()

        # For each gym, get top 2 fighters by last_fight_date
        stats = []
        for row in rows:
            # Query for notable fighters from this gym
            notable_query = (
                select(Fighter.name)
                .where(Fighter.training_gym == row.gym)
                .order_by(Fighter.last_fight_date.desc().nulls_last())
                .limit(2)
            )
            notable_result = await self._session.execute(notable_query)
            notable_fighters = [name for (name,) in notable_result.all()]

            stats.append(
                {
                    "gym": row.gym,
                    "city": row.city,
                    "country": row.country,
                    "fighter_count": row.fighter_count,
                    "notable_fighters": notable_fighters,
                }
            )

        return stats
