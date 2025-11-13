"""Utilities for computing upcoming and most recent fight status metadata."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Literal

from sqlalchemy import case, func, select

from backend.db.models import Event, Fight, Fighter


class FighterFightStatusMixin:
    """Provide helpers for describing a fighter's immediate fight outlook."""

    def _normalize_fight_result(
        self, result: str | None
    ) -> Literal["win", "loss", "draw", "nc"] | None:
        """Normalize fight result to canonical form."""

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
        return None

    async def _fetch_fight_status(
        self, fighter_ids: Sequence[str]
    ) -> dict[str, dict[str, date | Literal["win", "loss", "draw", "nc"] | None]]:
        """Fetch upcoming fight dates and last fight results for given fighters."""

        if not fighter_ids:
            return {}

        # Build subquery for fighters as fighter_id (primary fighter)
        next_fight_as_primary = (
            select(
                Fight.fighter_id.label("fighter_id"),
                Fight.event_date.label("next_fight_date"),
            )
            .join(Event, Fight.event_id == Event.id)
            .where(Fight.fighter_id.in_(fighter_ids))
            .where(Event.date > func.current_date())
            .where(Fight.result == "next")
        )

        # Build subquery for fighters as opponent_id (opponent fighter)
        next_fight_as_opponent = (
            select(
                Fight.opponent_id.label("fighter_id"),
                Fight.event_date.label("next_fight_date"),
            )
            .join(Event, Fight.event_id == Event.id)
            .where(Fight.opponent_id.in_(fighter_ids))
            .where(Event.date > func.current_date())
            .where(Fight.result == "next")
        )

        # Union both subqueries and group to get min date
        next_fight_union = next_fight_as_primary.union_all(next_fight_as_opponent).subquery()

        next_fight_subq = (
            select(
                next_fight_union.c.fighter_id,
                func.min(next_fight_union.c.next_fight_date).label("next_fight_date"),
            )
            .group_by(next_fight_union.c.fighter_id)
        ).subquery()

        last_fight_subq = (
            select(
                Fight.fighter_id.label("fighter_id"),
                Fight.result.label("last_result"),
                func.row_number()
                .over(
                    partition_by=Fight.fighter_id,
                    order_by=(
                        case(
                            (
                                Fight.result.in_(
                                    [
                                        "W",
                                        "L",
                                        "win",
                                        "loss",
                                        "draw",
                                        "nc",
                                        "NC",
                                        "no contest",
                                    ]
                                ),
                                0,
                            ),
                            else_=1,
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
