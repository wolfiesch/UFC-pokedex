"""Pure helpers that convert fight result rows into schema objects.

Keeping these functions isolated allows the repository to remain focused on
issuing SQL queries while still providing a reusable, well-documented pipeline
for transforming historical fight data.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from backend.db.repositories.base import _invert_fight_result
from backend.db.repositories.fight_utils import (
    create_fight_key,
    should_replace_fight,
    sort_fight_history,
)
from backend.schemas.fighter import FightHistoryEntry


def build_fight_history(
    *,
    fighter_id: str,
    fights: Sequence[Any],
    opponent_lookup: Mapping[str | None, str],
) -> list[FightHistoryEntry]:
    """Return a deduplicated, chronologically sorted fight history payload.

    Args:
        fighter_id: Unique identifier for the fighter whose history is being
            assembled. The value is not currently used to scope fights because
            the SQL queries provide already-filtered rows, but it is accepted to
            make the contract explicit for callers.
        fights: SQLAlchemy result rows representing primary and opponent
            perspectives of fights. Each row must expose the attributes used in
            :mod:`backend.db.repositories.fighter_repository` queries (for
            example ``fight_id``, ``event_name``, ``opponent_id``, and the
            ``is_primary`` flag).
        opponent_lookup: Mapping of fighter identifiers to their display names
            gathered in a single query for efficiency.

    Returns:
        Ordered list of :class:`FightHistoryEntry` instances suitable for API
        responses.
    """

    fight_dict: dict[tuple[str, str | None, str], FightHistoryEntry] = {}

    for row in fights:
        if row.is_primary:
            # When the fighter is the recorded ``fighter_id`` we can trust the
            # opponent information that comes with the row. Fallback to the
            # lookup so that histories survive sparse opponent names.
            opponent_id = row.opponent_id
            opponent_name = row.opponent_name or opponent_lookup.get(
                opponent_id, "Unknown"
            )
            fight_key = create_fight_key(
                row.event_name,
                row.event_date,
                opponent_id,
                opponent_name,
            )
            candidate = FightHistoryEntry(
                fight_id=row.fight_id,
                event_name=row.event_name,
                event_date=row.event_date,
                opponent=opponent_name,
                opponent_id=opponent_id,
                result=row.result,
                method=row.method or "",
                round=row.round,
                time=row.time,
                fight_card_url=row.fight_card_url,
                stats=row.stats,
            )
        else:
            # The fighter appeared as the ``opponent_id`` in storage. We flip
            # the result to retain their perspective.
            opponent_id = row.inverted_opponent_id
            opponent_name = opponent_lookup.get(opponent_id, "Unknown")
            fight_key = create_fight_key(
                row.event_name, row.event_date, opponent_id, opponent_name
            )
            inverted_result = _invert_fight_result(row.result)
            candidate = FightHistoryEntry(
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

        existing = fight_dict.get(fight_key)
        if existing is None:
            fight_dict[fight_key] = candidate
        elif should_replace_fight(existing.result, candidate.result):
            # Replace placeholder entries (for example, ``"N/A"`` results) with
            # rows that include authoritative fight outcomes.
            fight_dict[fight_key] = candidate

    # Convert dict to list and sort by event date using shared utility logic.
    fight_history = list(fight_dict.values())
    return sort_fight_history(fight_history)
