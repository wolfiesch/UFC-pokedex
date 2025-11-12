"""Streak computation helpers used by the fighter repository."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, cast

from sqlalchemy import func, literal, select, true, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Fight
from backend.db.repositories.base import _normalize_result_category

from .types import StreakType


async def batch_compute_streaks(
    session: AsyncSession,
    fighter_ids: Sequence[str],
    *,
    window: int | None = 6,
) -> dict[str, dict[str, int | StreakType]]:
    """Compute streaks for multiple fighters in a single database query."""

    if not fighter_ids:
        return {}

    unique_fighter_ids = list(dict.fromkeys(fighter_ids))
    if not unique_fighter_ids:
        return {}

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

    ordered = (
        select(
            combined.c.subject_id,
            combined.c.event_date,
            combined.c.result,
            func.row_number()
            .over(
                partition_by=combined.c.subject_id,
                order_by=combined.c.event_date.desc().nulls_last(),
            )
            .label("row_number"),
        ).select_from(combined)
    ).cte("ordered_subject_fights")

    if effective_window is not None:
        ordered = ordered.where(ordered.c.row_number <= effective_window)

    rows = await session.execute(
        select(
            ordered.c.subject_id,
            ordered.c.event_date,
            ordered.c.result,
            ordered.c.row_number,
        ).order_by(ordered.c.subject_id, ordered.c.row_number)
    )

    grouped: dict[str, list[tuple[int, str | None]]] = {}
    for subject_id, event_date, result, row_number in rows:
        entries = grouped.setdefault(subject_id, [])
        entries.append((row_number, result))

    streaks: dict[str, dict[str, int | StreakType]] = {}
    for subject_id, fight_entries in grouped.items():
        streaks[subject_id] = _compute_streak_from_entries(fight_entries, window=window)

    return streaks


def _compute_streak_from_entries(
    fight_entries: list[tuple[int, str | None]],
    *,
    window: int | None,
) -> dict[str, int | StreakType]:
    """Derive streak metadata from ordered fight result entries."""

    if not fight_entries:
        return {"current_streak_type": "none", "current_streak_count": 0}

    last_completed: Literal["win", "loss", "draw"] | None = None
    completed_seen = 0
    for _, result_text in fight_entries:
        category = _normalize_result_category(result_text)
        if category in {"win", "loss", "draw"}:
            last_completed = cast(Literal["win", "loss", "draw"], category)
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


async def compute_current_streak(
    session: AsyncSession,
    fighter_id: str,
    *,
    window: int = 6,
) -> dict[str, int | StreakType]:
    """Return the most recent decisive streak for ``fighter_id``."""

    result = await batch_compute_streaks(session, [fighter_id], window=window)
    return result.get(
        fighter_id,
        {"current_streak_type": "none", "current_streak_count": 0},
    )
