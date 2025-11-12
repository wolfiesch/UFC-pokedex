"""Test support repositories used to simulate fighter data sources."""

from __future__ import annotations

import secrets
from collections.abc import Iterable, Sequence
from datetime import date
from typing import Literal

from backend.db.repositories.fighter_repository import (
    FighterSearchFilters,
    filter_roster_entries,
    normalize_search_filters,
    paginate_roster_entries,
)
from backend.schemas.fighter import (
    FighterComparisonEntry,
    FighterDetail,
    FighterListItem,
)
from backend.services.fighter_query_service import FighterRepositoryProtocol


class InMemoryFighterRepository(FighterRepositoryProtocol):
    """Temporary repository used in tests and during local development."""

    def __init__(self) -> None:
        # Provide a deterministic sample fighter to keep unit tests predictable.
        self._fighters: dict[str, FighterDetail] = {
            "sample-fighter": FighterDetail(
                fighter_id="sample-fighter",
                detail_url="http://www.ufcstats.com/fighter-details/sample-fighter",
                name="Sample Fighter",
                nickname="Prototype",
                height="6'0\"",
                weight="170 lbs.",
                reach='74"',
                stance="Orthodox",
                dob=date(1990, 1, 1),
                record="10-2-0",
                striking={"sig_strikes_landed_per_min": 3.5},
                grappling={"takedown_accuracy": "45%"},
                fight_history=[],
            )
        }

    def _list_item_from_detail(self, detail: FighterDetail) -> FighterListItem:
        """Convert a stored fighter detail into a lightweight list item."""

        return FighterListItem.model_validate(detail.model_dump())

    async def list_fighters(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        nationality: str | None = None,
        birthplace_country: str | None = None,
        birthplace_city: str | None = None,
        training_country: str | None = None,
        training_city: str | None = None,
        training_gym: str | None = None,
        has_location_data: bool | None = None,
        include_streak: bool = False,
        streak_window: int = 6,
    ) -> Iterable[FighterListItem]:
        """Return fighters in insertion order while honouring pagination hints."""

        roster: list[FighterListItem] = [
            self._list_item_from_detail(detail) for detail in self._fighters.values()
        ]
        # Apply nationality filter if specified.
        if nationality:
            roster = [f for f in roster if f.nationality == nationality]
        # Add location filters (simple implementation for in-memory).
        if birthplace_country:
            roster = [f for f in roster if f.birthplace_country == birthplace_country]
        if training_gym:
            roster = [
                f
                for f in roster
                if f.training_gym and training_gym.lower() in f.training_gym.lower()
            ]
        return paginate_roster_entries(
            roster,
            limit=limit,
            offset=offset,
        )

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Return a stored fighter detail if present."""

        return self._fighters.get(fighter_id)

    async def search_fighters(
        self,
        *,
        query: str | None = None,
        stance: str | None = None,
        division: str | None = None,
        champion_statuses: list[str] | None = None,
        streak_type: Literal["win", "loss"] | None = None,
        min_streak_count: int | None = None,
        include_locations: bool = True,
        include_streak: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[list[FighterListItem], int]:
        """Search the in-memory roster using the repository helper utilities."""

        filters: FighterSearchFilters = normalize_search_filters(
            query=query,
            stance=stance,
            division=division,
            champion_statuses=champion_statuses,
            streak_type=streak_type,
            min_streak_count=min_streak_count,
        )

        roster = [
            self._list_item_from_detail(detail) for detail in self._fighters.values()
        ]
        filtered = filter_roster_entries(roster, filters=filters)
        paginated = list(
            paginate_roster_entries(
                filtered,
                limit=limit,
                offset=offset,
            )
        )
        return paginated, len(filtered)

    async def get_fighters_for_comparison(
        self, fighter_ids: Sequence[str]
    ) -> list[FighterComparisonEntry]:
        """Gather the subset of fighters requested for comparison."""

        fighters: list[FighterComparisonEntry] = []
        for fighter_id in fighter_ids:
            detail = self._fighters.get(fighter_id)
            if detail is None:
                # Skip unknown fighters to mirror repository behaviour.
                continue
            fighters.append(
                FighterComparisonEntry(
                    fighter_id=fighter_id,
                    name=detail.name,
                    record=detail.record,
                    division=detail.division,
                    striking=detail.striking,
                    grappling=detail.grappling,
                    significant_strikes=getattr(detail, "significant_strikes", {}),
                    takedown_stats=getattr(detail, "takedown_stats", {}),
                    career={},
                )
            )
        return fighters

    async def count_fighters(
        self,
        *,
        nationality: str | None = None,
        birthplace_country: str | None = None,
        birthplace_city: str | None = None,
        training_country: str | None = None,
        training_city: str | None = None,
        training_gym: str | None = None,
        has_location_data: bool | None = None,
    ) -> int:
        """Return a simple count, optionally filtered by nationality."""

        if nationality:
            return sum(
                1
                for detail in self._fighters.values()
                if getattr(detail, "nationality", None) == nationality
            )
        return len(self._fighters)

    async def get_random_fighter(self) -> FighterListItem | None:
        """Return a random fighter snapshot for teasers."""

        if not self._fighters:
            return None
        fighter_id = secrets.choice(list(self._fighters.keys()))
        detail = self._fighters[fighter_id]
        return self._list_item_from_detail(detail)


__all__ = ["InMemoryFighterRepository"]
