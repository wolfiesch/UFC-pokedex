"""Location aggregation collaborator used by :mod:`backend.services.stats_service`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from backend.db.repositories.fighter_repository import FighterRepository
from backend.schemas.stats import (
    CityStat,
    CityStatsResponse,
    CountryStat,
    CountryStatsResponse,
    GymStat,
    GymStatsResponse,
)

CountryGroupBy = Literal["birthplace", "training", "nationality"]
CityGroupBy = Literal["birthplace", "training"]
GymSortBy = Literal["count", "name"]


@dataclass(slots=True)
class LocationStatsAggregator:
    """Aggregate fighter counts per location with reusable filtering rules."""

    fighter_repository: FighterRepository

    async def get_country_stats(
        self,
        *,
        group_by: CountryGroupBy,
        min_fighters: int,
    ) -> CountryStatsResponse:
        """Return countries exceeding the provided fighter threshold."""

        stats, total = await self.fighter_repository.get_country_stats(group_by)

        # Filter any countries with a fighter count below the requested minimum so the
        # response focuses on meaningful concentrations of athletes.
        filtered_stats = [
            CountryStat(**entry) for entry in stats if entry["count"] >= min_fighters
        ]

        return CountryStatsResponse(
            group_by=group_by,
            countries=filtered_stats,
            total_fighters=total,
        )

    async def get_city_stats(
        self,
        *,
        group_by: CityGroupBy,
        country: str | None,
        min_fighters: int,
    ) -> CityStatsResponse:
        """Return city aggregates optionally scoped to a specific country."""

        stats, total = await self.fighter_repository.get_city_stats(group_by, country)

        # Apply the same minimum threshold to avoid returning sparsely populated cities
        # which rarely make for useful dashboard visualisations.
        filtered_stats = [
            CityStat(**entry) for entry in stats if entry["count"] >= min_fighters
        ]

        return CityStatsResponse(
            group_by=group_by,
            cities=filtered_stats,
            total_fighters=total,
        )

    async def get_gym_stats(
        self,
        *,
        country: str | None,
        min_fighters: int,
        sort_by: GymSortBy,
    ) -> GymStatsResponse:
        """Return gym aggregates filtered by fighter count and sorted deterministically."""

        stats = await self.fighter_repository.get_gym_stats(country)

        # Transform raw dictionaries into strongly-typed models while excluding gyms that
        # do not meet the caller's minimum fighter requirement.
        filtered_stats = [
            GymStat(**entry)
            for entry in stats
            if entry["fighter_count"] >= min_fighters
        ]

        if sort_by == "name":
            # Alphabetical ordering is helpful for search-like experiences in the UI.
            filtered_stats = sorted(filtered_stats, key=lambda stat: stat.gym)
        else:
            # Default to descending fighter counts to highlight the most prominent gyms.
            filtered_stats = sorted(
                filtered_stats,
                key=lambda stat: stat.fighter_count,
                reverse=True,
            )

        return GymStatsResponse(
            gyms=filtered_stats,
            total_gyms=len(filtered_stats),
        )


__all__ = [
    "CityGroupBy",
    "CountryGroupBy",
    "GymSortBy",
    "LocationStatsAggregator",
]
