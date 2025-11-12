"""Utilities for turning SQLAlchemy fight rows into schema objects.

The fighter repository retrieves raw SQLAlchemy rows that combine both the
"primary" and "opponent" perspectives of a bout.  The helpers in this module
transform those rows into the :class:`~backend.schemas.fighter.FightHistoryEntry`
models used by the API while keeping the repository methods narrowly focused on
executing the query itself.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any, cast

from sqlalchemy.engine import RowMapping

from backend.db.repositories.base import _invert_fight_result
from backend.db.repositories.fight_utils import (
    create_fight_key,
    should_replace_fight,
    sort_fight_history,
)
from backend.schemas.fighter import FightHistoryEntry

FightRow = RowMapping[str, Any]


def collect_opponent_ids(rows: Sequence[FightRow]) -> set[str]:
    """Return the set of opponent identifiers referenced by the fight rows."""

    opponent_ids: set[str] = set()
    for row in rows:
        opponent_id = cast(str | None, row.get("opponent_id"))
        if opponent_id:
            opponent_ids.add(opponent_id)
        inverted_opponent_id = cast(str | None, row.get("inverted_opponent_id"))
        if inverted_opponent_id:
            opponent_ids.add(inverted_opponent_id)
    return opponent_ids


def build_fight_history(
    rows: Sequence[FightRow],
    opponent_lookup: Mapping[str, str],
) -> list[FightHistoryEntry]:
    """Construct :class:`FightHistoryEntry` items from raw row data.

    The function deduplicates bouts by combining event metadata with opponent
    identifiers, prioritising the fighter-centric view of a bout when both
    fighters have scraped records.  Any missing opponent names are substituted
    using ``opponent_lookup`` so that the schema returned to the API layer is
    always complete.
    """

    fights: dict[tuple[str, str | None, str], FightHistoryEntry] = {}
    for row in rows:
        is_primary = bool(row.get("is_primary"))
        fight_id = cast(str | None, row.get("fight_id"))
        event_name = cast(str, row.get("event_name"))
        event_date = cast(date | None, row.get("event_date"))
        method = cast(str | None, row.get("method"))
        result = cast(str | None, row.get("result")) or "N/A"
        fight_card_url = cast(str | None, row.get("fight_card_url"))
        round_number = cast(str | None, row.get("round"))
        time_remaining = cast(str | None, row.get("time"))
        stats_blob = cast(Mapping[str, Any] | None, row.get("stats"))

        if is_primary:
            opponent_id = cast(str | None, row.get("opponent_id"))
            opponent_name = cast(
                str | None, row.get("opponent_name")
            ) or opponent_lookup.get(opponent_id or "", "Unknown")
            fight_key = create_fight_key(
                event_name, event_date, opponent_id, opponent_name
            )
            entry = FightHistoryEntry(
                fight_id=fight_id,
                event_name=event_name,
                event_date=event_date,
                opponent=opponent_name,
                opponent_id=opponent_id,
                result=result,
                method=method or "",
                round=round_number,
                time=time_remaining,
                fight_card_url=fight_card_url,
                stats=stats_blob,
            )
        else:
            opponent_id = cast(str | None, row.get("inverted_opponent_id"))
            opponent_name = opponent_lookup.get(opponent_id or "", "Unknown")
            fight_key = create_fight_key(
                event_name, event_date, opponent_id, opponent_name
            )
            inverted_result = _invert_fight_result(result)
            entry = FightHistoryEntry(
                fight_id=fight_id,
                event_name=event_name,
                event_date=event_date,
                opponent=opponent_name,
                opponent_id=opponent_id,
                result=inverted_result,
                method=method or "",
                round=round_number,
                time=time_remaining,
                fight_card_url=fight_card_url,
                stats=stats_blob,
            )

        if fight_key not in fights:
            fights[fight_key] = entry
        elif should_replace_fight(fights[fight_key].result, entry.result):
            fights[fight_key] = entry

    return sort_fight_history(list(fights.values()))
