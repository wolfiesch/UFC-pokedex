"""Utility functions for processing fight data and building fight history.

Extracted from fighter_repository.py to improve code organization and maintainability.
"""

from datetime import date

from backend.schemas.fighter import FightHistoryEntry


def create_fight_key(
    event_name: str,
    event_date: date | None,
    opponent_id: str | None,
    opponent_name: str,
) -> tuple[str, str | None, str]:
    """Create a unique key for fight deduplication based on metadata.

    Args:
        event_name: Name of the event
        event_date: Date of the event
        opponent_id: Database ID of opponent (preferred for matching)
        opponent_name: Name of opponent (fallback if ID not available)

    Returns:
        Tuple of (event_name, date_string, opponent_key) for use as dict key
    """
    date_str = event_date.isoformat() if event_date else None
    # Use opponent_id if available, otherwise use opponent_name (normalized)
    opponent_key = opponent_id if opponent_id else opponent_name.lower().strip()
    return (event_name, date_str, opponent_key)


def should_replace_fight(existing_result: str, new_result: str) -> bool:
    """Determine if new fight should replace existing based on result quality.

    Prefers actual results (win/loss/draw) over "N/A" placeholders.

    Args:
        existing_result: Current fight result in the dict
        new_result: New fight result being considered

    Returns:
        True if new result should replace existing, False otherwise
    """
    # Prefer actual results (win/loss/draw) over "N/A"
    if existing_result == "N/A" and new_result != "N/A":
        return True
    return False


def sort_fight_history(fights: list[FightHistoryEntry]) -> list[FightHistoryEntry]:
    """Sort fight history with upcoming fights first, then past fights by date.

    Args:
        fights: List of fight history entries to sort

    Returns:
        A new sorted list of fight history entries (input list is not modified)
    """
    sorted_fights = fights.copy()
    sorted_fights.sort(
        key=lambda fight: (
            # Primary: upcoming fights first (result="next" → 0, others → 1)
            0 if fight.result == "next" else 1,
            # Secondary: most recent first (use min date for nulls to push them last)
            -(fight.event_date or date.min).toordinal(),
        )
    )
    return sorted_fights


def compute_record_from_fights(fights: list[FightHistoryEntry]) -> str | None:
    """Compute fighter record (W-L-D) from fight history.

    Args:
        fights: List of fight history entries

    Returns:
        Record string in format "W-L-D" or None if no completed fights
    """
    from backend.db.repositories.base import _normalize_result_category

    if not fights:
        return None

    wins = sum(1 for fight in fights if _normalize_result_category(fight.result) == "win")
    losses = sum(1 for fight in fights if _normalize_result_category(fight.result) == "loss")
    draws = sum(1 for fight in fights if _normalize_result_category(fight.result) == "draw")

    # Only return computed record if at least one completed fight exists
    if wins + losses + draws > 0:
        return f"{wins}-{losses}-{draws}"

    return None
