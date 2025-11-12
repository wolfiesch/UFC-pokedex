"""Column selection utilities used by fighter repository mixins."""

from __future__ import annotations

from typing import Any

from backend.db.models import Fighter


def fighter_summary_columns() -> list[Any]:
    """Columns to load for fighter list/summary views."""

    return [
        Fighter.id,
        Fighter.name,
        Fighter.nickname,
        Fighter.record,
        Fighter.division,
        Fighter.height,
        Fighter.weight,
        Fighter.reach,
        Fighter.stance,
        Fighter.dob,
        Fighter.image_url,
        Fighter.is_current_champion,
        Fighter.is_former_champion,
        Fighter.current_streak_type,
        Fighter.current_streak_count,
        Fighter.last_fight_date,
        Fighter.birthplace,
        Fighter.birthplace_city,
        Fighter.birthplace_country,
        Fighter.nationality,
        Fighter.fighting_out_of,
        Fighter.training_gym,
        Fighter.training_city,
        Fighter.training_country,
    ]


def fighter_detail_columns() -> list[Any]:
    """Columns to load for detailed fighter views."""

    return [
        Fighter.id,
        Fighter.name,
        Fighter.nickname,
        Fighter.height,
        Fighter.weight,
        Fighter.reach,
        Fighter.stance,
        Fighter.dob,
        Fighter.image_url,
        Fighter.record,
        Fighter.leg_reach,
        Fighter.division,
        Fighter.is_current_champion,
        Fighter.is_former_champion,
        Fighter.championship_history,
        Fighter.birthplace,
        Fighter.birthplace_city,
        Fighter.birthplace_country,
        Fighter.nationality,
        Fighter.fighting_out_of,
        Fighter.training_gym,
        Fighter.training_city,
        Fighter.training_country,
    ]


def fighter_comparison_columns() -> list[Any]:
    """Columns to load for fighter comparison views."""

    return [
        Fighter.id,
        Fighter.name,
        Fighter.record,
        Fighter.division,
        Fighter.image_url,
        Fighter.is_current_champion,
        Fighter.is_former_champion,
    ]


__all__ = [
    "fighter_summary_columns",
    "fighter_detail_columns",
    "fighter_comparison_columns",
]
