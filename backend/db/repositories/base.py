"""Base repository utilities shared across all repository implementations.

This module provides common functions, constants, and utilities used by
specialized repositories to maintain consistency and reduce duplication.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Fight

# Global cache for database column support checks
_WAS_INTERIM_SUPPORTED_CACHE: bool | None = None

# Standard columns to load for fight history queries
_FIGHT_HISTORY_LOAD_COLUMNS = (
    Fight.id,
    Fight.fighter_id,
    Fight.opponent_id,
    Fight.opponent_name,
    Fight.event_name,
    Fight.event_date,
    Fight.result,
    Fight.method,
    Fight.round,
    Fight.time,
    Fight.fight_card_url,
    Fight.stats,
    Fight.weight_class,
)


def _invert_fight_result(result: str | None) -> str:
    """Invert a fight result from one fighter's perspective to the opponent's.

    Examples:
        'win' -> 'loss'
        'loss' -> 'win'
        'W' -> 'L'
        'draw' -> 'draw'
        'NC' -> 'NC'
    """
    if not result:
        return "Unknown"

    result_lower = result.lower().strip()

    # Handle common result formats
    if result_lower in ("w", "win"):
        return "loss"
    elif result_lower in ("l", "loss"):
        return "win"
    elif result_lower in ("d", "draw", "draw-majority", "draw-split"):
        return result  # Draws stay the same
    elif result_lower in ("nc", "no contest"):
        return result  # No contests stay the same
    elif result_lower == "next":
        return result  # Upcoming fights stay the same
    else:
        # Unknown result format, return as-is
        return result


def _normalize_result_category(result: str | None) -> str:
    """Normalize varying result strings into shared categories for analytics."""

    if result is None:
        return "other"

    normalized_result = result.strip().lower()
    if normalized_result in {"win", "w"}:
        return "win"
    if normalized_result in {"loss", "l"}:
        return "loss"
    if normalized_result.startswith("draw"):
        return "draw"
    if normalized_result in {"nc", "no contest"}:
        return "nc"
    if normalized_result == "next":
        return "upcoming"
    return "other"


def _empty_breakdown() -> dict[str, int]:
    """Return a pre-seeded result breakdown dictionary."""

    return {
        "win": 0,
        "loss": 0,
        "draw": 0,
        "nc": 0,
        "upcoming": 0,
        "other": 0,
    }


def _calculate_age(*, dob: date | None, reference_date: date) -> int | None:
    """Return the fighter's age in whole years relative to ``reference_date``.

    The repository persists birth dates as naive ``date`` objects.  To produce a
    consistent age value regardless of timezone or repeated invocations within a
    single request, the caller supplies a ``reference_date`` (typically the
    cached "today" value).  When a birth date is missing, the schema expects the
    age field to be ``None`` so API consumers can distinguish between unknown
    data and a legitimate age of zero.

    Args:
        dob: The fighter's date of birth, or ``None`` when the value is
            unavailable in the source dataset.
        reference_date: The "current" date used for the calculation.  Tests
            provide a deterministic value to keep expectations stable, while
            production calls use a timezone-aware UTC date snapshot.

    Returns:
        The integer age when ``dob`` is present.  ``None`` is returned for
        missing data, and ages are never negative—future-dated birthdays are
        clamped to zero so downstream code does not encounter surprising
        negative integers.
    """

    if dob is None:
        return None

    if dob > reference_date:
        # Guard against bad data entering the system by never returning a
        # negative age.  The value will be zero until the reference date moves
        # beyond the erroneous future birthday.
        return 0

    # Calculate years difference
    years_elapsed = reference_date.year - dob.year

    # Check if birthday has occurred this year
    has_had_birthday = (reference_date.month, reference_date.day) >= (
        dob.month,
        dob.day,
    )

    return years_elapsed - (not has_had_birthday)


class BaseRepository:
    """Base repository providing common functionality for all repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._was_interim_supported: bool | None = None

    async def _supports_was_interim(self) -> bool:
        """Check if the database schema supports the was_interim column."""
        global _WAS_INTERIM_SUPPORTED_CACHE

        if _WAS_INTERIM_SUPPORTED_CACHE is not None:
            self._was_interim_supported = _WAS_INTERIM_SUPPORTED_CACHE
            return _WAS_INTERIM_SUPPORTED_CACHE

        if self._was_interim_supported is not None:
            return self._was_interim_supported

        def check(sync_session: Any) -> bool:
            from backend.db.models import Fighter

            bind = sync_session.get_bind()
            inspector = inspect(bind)
            columns = inspector.get_columns(Fighter.__tablename__)
            return any(column["name"] == "was_interim" for column in columns)

        try:
            self._was_interim_supported = await self._session.run_sync(check)
        except Exception:
            self._was_interim_supported = False

        _WAS_INTERIM_SUPPORTED_CACHE = self._was_interim_supported
        return self._was_interim_supported

    async def _resolve_fighter_columns(
        self,
        base_columns: list[Any],
        *,
        include_was_interim: bool = True,
    ) -> tuple[list[Any], bool]:
        """Resolve which fighter columns to load based on schema support."""
        from backend.db.models import Fighter

        supports_was_interim = await self._supports_was_interim()
        columns = list(base_columns)
        if include_was_interim and supports_was_interim:
            columns.append(Fighter.was_interim)
        return columns, supports_was_interim
