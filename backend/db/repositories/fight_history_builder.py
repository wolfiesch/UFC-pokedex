"""Utilities for constructing fight history payloads from database rows.

The functions in this module intentionally avoid any database access. They
operate purely on SQLAlchemy row proxies and mappings so the calling repository
is responsible for fetching the required data while this module focuses on the
shape of the response.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from backend.db.repositories.base import _invert_fight_result
from backend.db.repositories.fight_utils import (
    compute_record_from_fights,
    create_fight_key,
    should_replace_fight,
    sort_fight_history,
)
from backend.schemas.fighter import FightHistoryEntry


class FightRow(Protocol):
    """Structural protocol describing the fight rows returned by the query."""

    fight_id: str | None
    event_name: str | None
    event_date: date | None
    opponent_id: str | None
    opponent_name: str | None
    result: str | None
    method: str | None
    round: int | None
    time: str | None
    fight_card_url: str | None
    stats: dict | None
    is_primary: bool
    inverted_opponent_id: str | None


@dataclass(slots=True)
class FightHistoryBuildResult:
    """Return payload that includes the deduplicated history and record stats."""

    fight_history: list[FightHistoryEntry]
    computed_record: str | None


def build_fight_history(
    rows: Iterable[FightRow],
    *,
    opponent_lookup: Mapping[str | None, str],
    existing_record: str | None,
) -> FightHistoryBuildResult:
    """Create API-ready fight history entries for ``fighter_id``.

    Args:
        rows: SQLAlchemy row objects containing combined primary/opponent fights.
        opponent_lookup: Mapping from fighter IDs to names used for display.
        existing_record: Record string already stored on the fighter model. When
            missing, we derive a fresh record from the resulting history.

    Returns:
        :class:`FightHistoryBuildResult` containing the sorted list of
        :class:`FightHistoryEntry` objects and a potentially recomputed record.
    """

    fight_dict: dict[tuple[str, date | None, str | None, str], FightHistoryEntry] = {}

    for row in rows:
        if row.is_primary:
            opponent_id = row.opponent_id
            opponent_name = _coalesce_opponent_name(
                opponent_lookup, opponent_id, row.opponent_name
            )
            fight_key = create_fight_key(
                row.event_name, row.event_date, opponent_id, opponent_name
            )
            entry = _create_entry_from_row(
                row, opponent_id, opponent_name, result=row.result
            )
        else:
            opponent_id = row.inverted_opponent_id
            opponent_name = _coalesce_opponent_name(opponent_lookup, opponent_id, None)
            fight_key = create_fight_key(
                row.event_name, row.event_date, opponent_id, opponent_name
            )
            inverted_result = _invert_fight_result(row.result)
            entry = _create_entry_from_row(
                row,
                opponent_id,
                opponent_name,
                result=inverted_result,
            )

        existing_entry = fight_dict.get(fight_key)
        if existing_entry is None:
            fight_dict[fight_key] = entry
            continue

        if should_replace_fight(existing_entry.result, entry.result):
            fight_dict[fight_key] = entry

    fight_history = sort_fight_history(list(fight_dict.values()))
    computed_record = existing_record or compute_record_from_fights(fight_history)

    return FightHistoryBuildResult(
        fight_history=fight_history,
        computed_record=computed_record,
    )


def _coalesce_opponent_name(
    opponent_lookup: Mapping[str | None, str],
    opponent_id: str | None,
    row_value: str | None,
) -> str:
    """Return the best opponent name available for display."""

    if row_value:
        return row_value
    if opponent_id and opponent_id in opponent_lookup:
        return opponent_lookup[opponent_id]
    return "Unknown"


def _create_entry_from_row(
    row: FightRow,
    opponent_id: str | None,
    opponent_name: str,
    *,
    result: str | None,
) -> FightHistoryEntry:
    """Transform a SQLAlchemy row into a :class:`FightHistoryEntry`."""

    return FightHistoryEntry(
        fight_id=row.fight_id,
        event_name=row.event_name,
        event_date=row.event_date,
        opponent=opponent_name,
        opponent_id=opponent_id,
        result=result,
        method=row.method or "",
        round=row.round,
        time=row.time,
        fight_card_url=row.fight_card_url,
        stats=row.stats,
    )
