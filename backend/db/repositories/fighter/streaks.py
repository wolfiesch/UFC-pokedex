"""Streak computation utilities shared by fighter repository mixins."""

from __future__ import annotations

from datetime import date
from typing import Literal

from sqlalchemy import func, literal, select, true, union_all

from backend.db.models import Fight
from backend.db.repositories.base import (
    BaseRepository,
    _invert_fight_result,
    _normalize_result_category,
)

StreakLiteral = Literal["win", "loss", "draw", "none"]


class FighterStreakMixin(BaseRepository):
    """Provide reusable streak computation helpers for fighter repositories."""

    async def _batch_compute_streaks(
        self,
        fighter_ids: list[str],
        *,
        window: int | None = 6,
    ) -> dict[str, dict[str, int | StreakLiteral]]:
        """Compute streaks for multiple fighters in a single database query."""

        if not fighter_ids:
            return {}

        unique_fighter_ids = list(dict.fromkeys(fighter_ids))
        if not unique_fighter_ids:
            return {}
        fighter_ids = unique_fighter_ids

        effective_window: int | None = None if window is None else max(2, window)

        fighter_id_selects = [
            select(literal(f_id).label("fighter_id")) for f_id in unique_fighter_ids
        ]
        if len(fighter_id_selects) == 1:
            target_fighters = fighter_id_selects[0].cte("target_fighters")
        else:
            target_fighters = union_all(*fighter_id_selects).cte("target_fighters")

        order_clause = Fight.event_date.desc().nulls_last()

        primary_fights = (
            select(
                Fight.event_date.label("event_date"),
                Fight.result.label("result"),
            )
            .where(Fight.fighter_id == target_fighters.c.fighter_id)
            .order_by(order_clause)
        ).lateral("primary_fights")

        opponent_fights = (
            select(
                Fight.event_date.label("event_date"),
                Fight.result.label("result"),
            )
            .where(Fight.opponent_id == target_fighters.c.fighter_id)
            .order_by(order_clause)
        ).lateral("opponent_fights")

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

        if effective_window is not None:
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

        streaks: dict[str, dict[str, int | StreakLiteral]] = {}
        for fighter_id, fight_entries in fights_by_fighter.items():
            streaks[fighter_id] = self._compute_streak_from_fights(
                fight_entries, effective_window
            )

        return streaks

    def _compute_streak_from_fights(
        self,
        fight_entries: list[tuple[date | None, str]],
        window: int | None,
    ) -> dict[str, int | StreakLiteral]:
        """Compute streak from a list of fight entries (date, result pairs)."""

        if not fight_entries:
            return {"current_streak_type": "none", "current_streak_count": 0}

        fight_entries.sort(
            key=lambda entry: (entry[0] is None, entry[0] or date.min), reverse=True
        )

        last_completed: Literal["win", "loss", "draw"] | None = None
        completed_seen = 0
        for _, result_text in fight_entries:
            category = _normalize_result_category(result_text)
            if category in {"win", "loss", "draw"}:
                last_completed = category  # type: ignore[assignment]
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
    ) -> dict[str, int | StreakLiteral]:
        """Return the most recent decisive streak for ``fighter_id``."""

        result = await self._batch_compute_streaks([fighter_id], window=window)
        return result.get(
            fighter_id, {"current_streak_type": "none", "current_streak_count": 0}
        )


__all__ = ["FighterStreakMixin", "StreakLiteral"]
