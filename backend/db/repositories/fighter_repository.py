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

from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime
from typing import Any, Literal
from typing import cast as typing_cast

from sqlalchemy import func, literal, select, true, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from backend.db.models import Fight, Fighter, fighter_stats
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
        streak_by_fighter: dict[
            str, dict[str, int | Literal["win", "loss", "draw", "none"]]
        ] = {}
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
                        streak_by_fighter.get(fighter.id, {}).get(
                            "current_streak_type", "none"
                        )
                        if include_streak
                        else "none"
                    ),
                ),
                current_streak_count=(
                    int(
                        streak_by_fighter.get(fighter.id, {}).get(
                            "current_streak_count", 0
                        )
                    )
                    if include_streak
                    else 0
                ),
            )
            for fighter in fighters
        ]

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Get detailed fighter information by ID with optimized single-query fetch."""
        from sqlalchemy.orm import selectinload

        # Query fighter details with eager-loaded fights using selectinload
        # This uses a single JOIN query to load fighter + all fights (no N+1)
        base_columns = self._fighter_detail_columns()
        load_columns, supports_was_interim = await self._resolve_fighter_columns(
            base_columns
        )
        fighter_query = (
            select(Fighter)
            .options(
                load_only(*load_columns),
                selectinload(Fighter.fights),  # Eager load fights to prevent N+1
            )
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

        # Get fights from relationship (already loaded via selectinload - no additional query!)
        primary_fights = [f for f in fighter.fights]

        # Query fights from opponent's perspective (where this fighter is opponent_id)
        # Join with Fighter table to get opponent names in a single query
        opponent_fights_result = await self._session.execute(
            select(Fight, Fighter.name.label("fighter_name"))
            .join(Fighter, Fight.fighter_id == Fighter.id, isouter=True)
            .where(Fight.opponent_id == fighter_id)
            .order_by(Fight.event_date.desc().nulls_last(), Fight.id)
        )
        opponent_fights_with_names = opponent_fights_result.all()
        opponent_fights = [row[0] for row in opponent_fights_with_names]
        # Build a lookup for opponent names from the joined query
        opponent_fights_names_lookup = {
            row[0].id: row[1] or "Unknown" for row in opponent_fights_with_names
        }

        all_fights = list(primary_fights) + list(opponent_fights)

        # Build fight history, deduplicating by fight metadata (not database ID)
        # This prevents duplicate entries when both fighters have Fight records for the same bout
        # Prioritize fights where fighter_id matches (fighter's own perspective)
        # Also prioritize fights with actual results (win/loss/draw) over "N/A"
        fight_dict: dict[tuple[str, str | None, str], FightHistoryEntry] = {}

        # First pass: Process fights where this fighter is the primary fighter_id
        for fight in all_fights:
            if fight.fighter_id == fighter_id:
                fight_key = create_fight_key(
                    fight.event_name,
                    fight.event_date,
                    fight.opponent_id,
                    fight.opponent_name,
                )

                new_entry = FightHistoryEntry(
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
                    stats=fight.stats,
                )

                if fight_key not in fight_dict:
                    fight_dict[fight_key] = new_entry
                elif should_replace_fight(fight_dict[fight_key].result, fight.result):
                    # Replace with better result
                    fight_dict[fight_key] = new_entry

        # Collect unique opponent identifiers for primary fights only
        # (opponent fights already have names from the JOIN above)
        opponent_ids: set[str] = set()
        for fight in primary_fights:
            if fight.opponent_id:
                opponent_ids.add(fight.opponent_id)

        # Also collect fighter_ids from opponent fights for name lookup
        for fight in opponent_fights:
            opponent_ids.add(fight.fighter_id)

        opponent_lookup: dict[str, str] = {}
        if opponent_ids:
            opponent_rows = await self._session.execute(
                select(Fighter.id, Fighter.name).where(Fighter.id.in_(opponent_ids))
            )
            opponent_lookup = {row.id: row.name for row in opponent_rows.all()}

        # Merge with opponent fights names from JOIN
        opponent_lookup.update(opponent_fights_names_lookup)

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

                new_entry = FightHistoryEntry(
                    fight_id=fight.id,
                    event_name=fight.event_name,
                    event_date=fight.event_date,
                    opponent=opponent_name,
                    opponent_id=opponent_id,  # The original fighter_id is now the opponent
                    result=inverted_result,
                    method=fight.method or "",
                    round=fight.round,
                    time=fight.time,
                    fight_card_url=fight.fight_card_url,
                    stats=fight.stats,
                )

                if fight_key not in fight_dict:
                    fight_dict[fight_key] = new_entry
                elif should_replace_fight(fight_dict[fight_key].result, inverted_result):
                    # Replace with better result
                    fight_dict[fight_key] = new_entry

        # Convert dict to list and sort
        fight_history: list[FightHistoryEntry] = list(fight_dict.values())
        fight_history = sort_fight_history(fight_history)

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
            filters.append((Fighter.name.ilike(pattern)) | (Fighter.nickname.ilike(pattern)))
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

        # Streak filtering using pre-computed columns (Phase 2 optimization)
        if streak_type and min_streak_count:
            filters.append(Fighter.current_streak_type == streak_type)
            filters.append(Fighter.current_streak_count >= min_streak_count)

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

        # Use a single "today" snapshot so every returned card displays the same
        # age even if the request straddles midnight in UTC.
        today_utc: date = datetime.now(tz=UTC).date()

        # Phase 2: Streak data now comes from pre-computed database columns
        # No need to compute streaks - they're already in the Fighter model!

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
                    # Phase 2: Use pre-computed streak columns from database
                    current_streak_type=(
                        (_validate_streak_type(fighter.current_streak_type) or "none")
                        if include_streak
                        else "none"
                    ),
                    current_streak_count=(
                        fighter.current_streak_count if include_streak else 0
                    ),
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
                    was_interim=(fighter.was_interim if supports_was_interim else False),
                )
            )

        return comparison

    async def count_fighters(self) -> int:
        """Get the total count of fighters in the database."""
        query = select(func.count()).select_from(Fighter)
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
            select(Fighter).options(load_only(Fighter.id)).where(Fighter.id == fighter_id)
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
            stmt = (
                select(
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
                )
                .order_by(combined.c.subject_id, combined.c.event_date.desc().nulls_last())
            )
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
