"""Concrete fighter repository assembled from modular mixins."""

from __future__ import annotations

import os
from datetime import date
from typing import Any, Literal, Sequence, cast

from backend.db.models import Fighter
from backend.db.repositories.base import (
    BaseRepository,
    _calculate_age as _base_calculate_age,
    _invert_fight_result as _base_invert_fight_result,
)
from backend.schemas.fighter import (
    FighterComparisonEntry,
    FighterDetail,
    FighterListItem,
    FightHistoryEntry,
)
from backend.services.image_resolver import resolve_fighter_image

from .analytics import FighterAnalyticsMixin
from .detail import FighterDetailMixin
from .fight_status import fetch_fight_status, normalize_fight_result
from .mutations import FighterMutationMixin
from .ranking import fetch_ranking_summaries
from .roster import FighterRosterMixin
from .streaks import batch_compute_streaks, compute_current_streak
from .types import FighterRankingSummary

_DEFAULT_RANKING_SOURCE = (
    os.getenv("FIGHTER_RANKING_SOURCE")
    or os.getenv("DEFAULT_RANKING_SOURCE")
    or "fightmatrix"
).strip() or None


class FighterRepository(
    BaseRepository,
    FighterRosterMixin,
    FighterDetailMixin,
    FighterMutationMixin,
    FighterAnalyticsMixin,
):
    """Repository for fighter CRUD operations and queries."""

    def _fighter_summary_columns(self) -> list[Any]:
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

    def _fighter_detail_columns(self) -> list[Any]:
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

    def _fighter_comparison_columns(self) -> list[Any]:
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

    def _ranking_source(self) -> str | None:
        """Return the preferred ranking source for roster adornments."""

        return _DEFAULT_RANKING_SOURCE

    async def _fetch_ranking_summaries(
        self, fighter_ids: Sequence[str]
    ) -> dict[str, FighterRankingSummary]:
        """Delegate ranking lookups to the shared helper."""

        return await fetch_ranking_summaries(
            self._session, fighter_ids, ranking_source=self._ranking_source()
        )

    async def _fetch_fight_status(
        self, fighter_ids: Sequence[str]
    ) -> dict[str, dict[str, date | Literal["win", "loss", "draw", "nc"] | None]]:
        """Expose fight status helper for backward compatibility."""

        return await fetch_fight_status(self._session, fighter_ids)

    async def _batch_compute_streaks(
        self,
        fighter_ids: Sequence[str],
        *,
        window: int | None = 6,
    ) -> dict[str, dict[str, int | Literal["win", "loss", "draw", "none"]]]:
        """Preserve historical method for scripts/tests relying on direct access."""

        return await batch_compute_streaks(self._session, fighter_ids, window=window)

    async def _compute_current_streak(
        self,
        fighter_id: str,
        *,
        window: int = 6,
    ) -> dict[str, int | Literal["win", "loss", "draw", "none"]]:
        """Compatibility wrapper around the streak computation helper."""

        return await compute_current_streak(self._session, fighter_id, window=window)

    def _build_roster_entry(
        self,
        *,
        fighter: Fighter,
        supports_was_interim: bool,
        include_streak: bool,
        streak_bundle: dict[str, int | Literal["win", "loss", "draw", "none"]],
        fight_status: dict[str, date | Literal["win", "loss", "draw", "nc"] | None],
        ranking: FighterRankingSummary | None,
        today_utc: date,
    ) -> FighterListItem:
        """Assemble a ``FighterListItem`` from shared data pieces."""

        return FighterListItem(
            fighter_id=fighter.id,
            detail_url=f"http://www.ufcstats.com/fighter-details/{fighter.id}",
            name=fighter.name,
            nickname=fighter.nickname,
            record=fighter.record,
            division=fighter.division,
            height=fighter.height,
            weight=fighter.weight,
            reach=fighter.reach,
            stance=fighter.stance,
            dob=fighter.dob,
            image_url=resolve_fighter_image(fighter.id, fighter.image_url),
            age=self._calculate_age(
                dob=fighter.dob,
                reference_date=today_utc,
            ),
            is_current_champion=fighter.is_current_champion,
            is_former_champion=fighter.is_former_champion,
            was_interim=fighter.was_interim if supports_was_interim else False,
            current_streak_type=cast(
                Literal["win", "loss", "draw", "none"],
                (
                    streak_bundle.get("current_streak_type", "none")
                    if include_streak
                    else "none"
                ),
            ),
            current_streak_count=(
                int(streak_bundle.get("current_streak_count", 0))
                if include_streak
                else 0
            ),
            current_rank=ranking.current_rank if ranking else None,
            current_rank_date=ranking.current_rank_date if ranking else None,
            current_rank_division=ranking.current_rank_division if ranking else None,
            current_rank_source=ranking.current_rank_source if ranking else None,
            peak_rank=ranking.peak_rank if ranking else None,
            peak_rank_date=ranking.peak_rank_date if ranking else None,
            peak_rank_division=ranking.peak_rank_division if ranking else None,
            peak_rank_source=ranking.peak_rank_source if ranking else None,
            birthplace=fighter.birthplace,
            birthplace_city=fighter.birthplace_city,
            birthplace_country=fighter.birthplace_country,
            nationality=fighter.nationality,
            fighting_out_of=fighter.fighting_out_of,
            training_gym=fighter.training_gym,
            training_city=fighter.training_city,
            training_country=fighter.training_country,
            next_fight_date=cast(date | None, fight_status.get("next_fight_date")),
            last_fight_date=fighter.last_fight_date,
            last_fight_result=cast(
                Literal["win", "loss", "draw", "nc"] | None,
                fight_status.get("last_fight_result"),
            ),
        )

    def _build_fight_history_entry(
        self,
        *,
        row: Any,
        opponent_id: str | None,
        opponent_name: str | None,
        result_value: str | None,
    ) -> FightHistoryEntry:
        """Create a consistent ``FightHistoryEntry`` object from query rows."""

        return FightHistoryEntry(
            fight_id=row.fight_id,
            event_name=row.event_name,
            event_date=row.event_date,
            opponent=opponent_name or "Unknown",
            opponent_id=opponent_id,
            result=result_value,
            method=row.method or "",
            round=row.round,
            time=row.time,
            fight_card_url=row.fight_card_url,
            stats=row.stats,
        )

    def _build_fighter_detail(
        self,
        *,
        fighter: Fighter,
        supports_was_interim: bool,
        computed_record: str | None,
        stats_map: dict[str, dict[str, str]],
        fight_history: list[FightHistoryEntry],
        fighter_age: int | None,
        ranking_summary: FighterRankingSummary | None,
    ) -> FighterDetail:
        """Construct the ``FighterDetail`` response payload."""

        return FighterDetail(
            fighter_id=fighter.id,
            detail_url=f"http://www.ufcstats.com/fighter-details/{fighter.id}",
            name=fighter.name,
            nickname=fighter.nickname,
            height=fighter.height,
            weight=fighter.weight,
            reach=fighter.reach,
            stance=fighter.stance,
            dob=fighter.dob,
            image_url=resolve_fighter_image(fighter.id, fighter.image_url),
            record=computed_record,
            leg_reach=fighter.leg_reach,
            division=fighter.division,
            age=fighter_age,
            striking=stats_map.get("striking", {}),
            grappling=stats_map.get("grappling", {}),
            significant_strikes=stats_map.get("significant_strikes", {}),
            takedown_stats=stats_map.get("takedown_stats", {}),
            career=stats_map.get("career", {}),
            fight_history=fight_history,
            is_current_champion=fighter.is_current_champion,
            is_former_champion=fighter.is_former_champion,
            was_interim=fighter.was_interim if supports_was_interim else False,
            championship_history=fighter.championship_history or {},
            current_rank=ranking_summary.current_rank if ranking_summary else None,
            current_rank_date=(
                ranking_summary.current_rank_date if ranking_summary else None
            ),
            current_rank_division=(
                ranking_summary.current_rank_division if ranking_summary else None
            ),
            current_rank_source=(
                ranking_summary.current_rank_source if ranking_summary else None
            ),
            peak_rank=ranking_summary.peak_rank if ranking_summary else None,
            peak_rank_date=ranking_summary.peak_rank_date if ranking_summary else None,
            peak_rank_division=(
                ranking_summary.peak_rank_division if ranking_summary else None
            ),
            peak_rank_source=(
                ranking_summary.peak_rank_source if ranking_summary else None
            ),
            birthplace=fighter.birthplace,
            birthplace_city=fighter.birthplace_city,
            birthplace_country=fighter.birthplace_country,
            nationality=fighter.nationality,
            fighting_out_of=fighter.fighting_out_of,
            training_gym=fighter.training_gym,
            training_city=fighter.training_city,
            training_country=fighter.training_country,
        )

    def _build_comparison_entry(
        self,
        *,
        fighter: Fighter,
        stats_map: dict[str, dict[str, str]],
        supports_was_interim: bool,
        today_utc: date,
    ) -> FighterComparisonEntry:
        """Compose the payload for the fighter comparison endpoint."""

        return FighterComparisonEntry(
            fighter_id=fighter.id,
            name=fighter.name,
            record=fighter.record,
            division=fighter.division,
            striking=stats_map.get("striking", {}),
            grappling=stats_map.get("grappling", {}),
            significant_strikes=stats_map.get("significant_strikes", {}),
            takedown_stats=stats_map.get("takedown_stats", {}),
            career=stats_map.get("career", {}),
            age=self._calculate_age(
                dob=fighter.dob,
                reference_date=today_utc,
            ),
            is_current_champion=fighter.is_current_champion,
            is_former_champion=fighter.is_former_champion,
            was_interim=fighter.was_interim if supports_was_interim else False,
        )

    def _invert_fight_result(self, result: str | None) -> str:
        """Invert fight results using the shared base helper."""

        return _base_invert_fight_result(result)

    def _calculate_age(self, *, dob: date | None, reference_date: date) -> int | None:
        """Proxy to the canonical age calculation helper for mixins."""

        return _base_calculate_age(dob=dob, reference_date=reference_date)

    def _normalize_fight_result(
        self, result: str | None
    ) -> Literal["win", "loss", "draw", "nc"] | None:
        """Expose normalized fight results for legacy calls."""

        return normalize_fight_result(result)


__all__ = ["FighterRepository"]
