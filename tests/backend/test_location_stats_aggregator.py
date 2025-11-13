from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.db.repositories.fighter_repository import FighterRepository
from backend.schemas.stats import (
    CityStatsResponse,
    CountryStatsResponse,
    GymStatsResponse,
)
from backend.services.stats.location_stats_aggregator import LocationStatsAggregator


@pytest.mark.asyncio
async def test_country_stats_filters_minimum_threshold() -> None:
    """Countries below the minimum fighter count should be excluded."""

    repository = AsyncMock(spec=FighterRepository)
    repository.get_country_stats.return_value = (
        [
            {"country": "USA", "count": 10, "percentage": 50.0},
            {"country": "Canada", "count": 3, "percentage": 15.0},
        ],
        20,
    )

    aggregator = LocationStatsAggregator(repository)

    response: CountryStatsResponse = await aggregator.get_country_stats(
        group_by="birthplace",
        min_fighters=5,
    )

    repository.get_country_stats.assert_awaited_once_with("birthplace")
    assert [country.country for country in response.countries] == ["USA"]
    assert response.total_fighters == 20


@pytest.mark.asyncio
async def test_city_stats_filters_and_passes_country() -> None:
    """City aggregation should respect country filters and thresholds."""

    repository = AsyncMock(spec=FighterRepository)
    repository.get_city_stats.return_value = (
        [
            {"city": "Las Vegas", "country": "USA", "count": 8, "percentage": 40.0},
            {"city": "Toronto", "country": "Canada", "count": 2, "percentage": 10.0},
        ],
        10,
    )

    aggregator = LocationStatsAggregator(repository)

    response: CityStatsResponse = await aggregator.get_city_stats(
        group_by="training",
        country="USA",
        min_fighters=3,
    )

    repository.get_city_stats.assert_awaited_once_with("training", "USA")
    assert [city.city for city in response.cities] == ["Las Vegas"]
    assert response.total_fighters == 10


@pytest.mark.asyncio
async def test_gym_stats_sorting_by_name() -> None:
    """Gym aggregation should provide deterministic alphabetical ordering when requested."""

    repository = AsyncMock(spec=FighterRepository)
    repository.get_gym_stats.return_value = [
        {
            "gym": "Sanford MMA",
            "city": "Deerfield Beach",
            "country": "USA",
            "fighter_count": 12,
            "notable_fighters": ["Fighter A"],
        },
        {
            "gym": "American Top Team",
            "city": "Coconut Creek",
            "country": "USA",
            "fighter_count": 15,
            "notable_fighters": ["Fighter B"],
        },
        {
            "gym": "Kings MMA",
            "city": "Huntington Beach",
            "country": "USA",
            "fighter_count": 4,
            "notable_fighters": ["Fighter C"],
        },
    ]

    aggregator = LocationStatsAggregator(repository)

    response_name: GymStatsResponse = await aggregator.get_gym_stats(
        country=None,
        min_fighters=5,
        sort_by="name",
    )

    repository.get_gym_stats.assert_awaited_once_with(None)
    assert [gym.gym for gym in response_name.gyms] == [
        "American Top Team",
        "Sanford MMA",
    ]

    response_count: GymStatsResponse = await aggregator.get_gym_stats(
        country=None,
        min_fighters=5,
        sort_by="count",
    )

    assert [gym.gym for gym in response_count.gyms] == [
        "American Top Team",
        "Sanford MMA",
    ]
    assert [gym.fighter_count for gym in response_count.gyms] == [15, 12]
