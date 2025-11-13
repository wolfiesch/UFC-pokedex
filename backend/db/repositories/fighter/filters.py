"""Roster filtering helpers used by fighter repository mixins."""

from __future__ import annotations

from collections.abc import Iterable

from backend.db.repositories.fighter.types import (
    FighterSearchFilters,
    RosterEntry,
    StreakType,
)


def _validate_streak_type(value: str | None) -> StreakType | None:
    """Return a canonical streak literal for ``value`` when possible."""

    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in {"win", "loss", "draw", "none"}:
        msg = f"Invalid streak type: {value}"
        raise ValueError(msg)
    return normalized  # type: ignore[return-value]


def normalize_search_filters(
    *,
    query: str | None,
    stance: str | None,
    division: str | None,
    champion_statuses: Iterable[str] | None,
    streak_type: str | None,
    min_streak_count: int | None,
) -> FighterSearchFilters:
    """Return sanitized search inputs for consistent roster filtering."""

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
            msg = "streak_type must be either 'win' or 'loss' when searching fighters"
            raise ValueError(msg)

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
