"""Presentation-focused fighter service composing rich response models."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from typing import Literal, cast

from backend.db.models import Fighter
from backend.db.repositories.base import _calculate_age, _invert_fight_result
from backend.db.repositories.fight_utils import (
    compute_record_from_fights,
    create_fight_key,
    should_replace_fight,
    sort_fight_history,
)
from backend.db.repositories.fighter_repository import (
    FighterFightRow,
    FighterRankingSummary,
    FighterRepository,
)
from backend.schemas.fighter import (
    FighterComparisonEntry,
    FighterDetail,
    FighterListItem,
    FightHistoryEntry,
)
from backend.services.image_resolver import resolve_fighter_image


class FighterPresentationService:
    """Compose Pydantic fighter schemas from repository-level data accessors."""

    def __init__(self, repository: FighterRepository) -> None:
        """Initialize the service with its backing repository dependency."""

        self._repository = repository

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
    ) -> list[FighterListItem]:
        """Return fully-populated list items honouring roster filters."""

        fighters = await self._repository.list_fighters(
            limit=limit,
            offset=offset,
            nationality=nationality,
            birthplace_country=birthplace_country,
            birthplace_city=birthplace_city,
            training_country=training_country,
            training_city=training_city,
            training_gym=training_gym,
            has_location_data=has_location_data,
        )

        fighter_ids = [fighter.id for fighter in fighters]
        ranking_map = (
            await self._repository.get_ranking_summaries(fighter_ids)
            if fighter_ids
            else {}
        )
        status_map = (
            await self._repository.get_fight_status(fighter_ids) if fighter_ids else {}
        )
        streak_map = (
            await self._repository.get_current_streaks(
                list(fighter_ids), window=streak_window
            )
            if include_streak and fighter_ids
            else {}
        )

        today = datetime.now(tz=UTC).date()
        return [
            self._build_list_item(
                fighter,
                include_streak=include_streak,
                today=today,
                ranking=ranking_map.get(fighter.id),
                fight_status=status_map.get(fighter.id),
                streak_data=streak_map.get(fighter.id),
            )
            for fighter in fighters
        ]

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
        """Search fighters and return list items plus the total match count."""

        fighters, total = await self._repository.search_fighters(
            query=query,
            stance=stance,
            division=division,
            champion_statuses=champion_statuses,
            streak_type=streak_type,
            min_streak_count=min_streak_count,
            include_locations=include_locations,
            limit=limit,
            offset=offset,
        )

        fighter_ids = [fighter.id for fighter in fighters]
        ranking_map = (
            await self._repository.get_ranking_summaries(fighter_ids)
            if fighter_ids
            else {}
        )
        status_map = (
            await self._repository.get_fight_status(fighter_ids) if fighter_ids else {}
        )
        streak_map = (
            await self._repository.get_current_streaks(list(fighter_ids), window=6)
            if include_streak and fighter_ids
            else {}
        )

        today = datetime.now(tz=UTC).date()
        items = [
            self._build_list_item(
                fighter,
                include_streak=include_streak,
                today=today,
                ranking=ranking_map.get(fighter.id),
                fight_status=status_map.get(fighter.id),
                streak_data=streak_map.get(fighter.id),
            )
            for fighter in fighters
        ]
        return items, total

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Return a detailed fighter representation."""

        fighter = await self._repository.get_fighter(fighter_id)
        if fighter is None:
            return None

        fights = await self._repository.get_fighter_fights(fighter_id)
        opponent_ids = self._collect_opponent_ids(fights)
        opponent_names = await self._repository.get_fighter_name_map(opponent_ids)

        fight_history = self._build_fight_history(fights, opponent_names)
        computed_record = fighter.record or compute_record_from_fights(fight_history)
        stats_map = await self._repository.get_fighter_stats_map([fighter.id])
        ranking_summary = (
            await self._repository.get_ranking_summaries([fighter.id])
        ).get(fighter.id)
        status_map = (await self._repository.get_fight_status([fighter.id])).get(
            fighter.id, {}
        )

        today = datetime.now(tz=UTC).date()
        list_item = self._build_list_item(
            fighter,
            include_streak=True,
            today=today,
            ranking=ranking_summary,
            fight_status=status_map,
            streak_data={
                "current_streak_type": cast(
                    Literal["win", "loss", "draw", "none"],
                    fighter.current_streak_type or "none",
                ),
                "current_streak_count": fighter.current_streak_count or 0,
            },
        )

        stats_for_fighter = stats_map.get(fighter.id, {})
        return FighterDetail(
            **list_item.model_dump(mode="python"),
            record=computed_record,
            leg_reach=fighter.leg_reach,
            striking=stats_for_fighter.get("striking", {}),
            grappling=stats_for_fighter.get("grappling", {}),
            significant_strikes=stats_for_fighter.get("significant_strikes", {}),
            takedown_stats=stats_for_fighter.get("takedown_stats", {}),
            career=stats_for_fighter.get("career", {}),
            fight_history=fight_history,
            championship_history=fighter.championship_history or {},
        )

    async def get_fighters_for_comparison(
        self, fighter_ids: Sequence[str]
    ) -> list[FighterComparisonEntry]:
        """Return comparison entries preserving the input order."""

        fighters = await self._repository.get_fighters_for_comparison(fighter_ids)
        if not fighters:
            return []

        stats_map = await self._repository.get_fighter_stats_map(
            [fighter.id for fighter in fighters]
        )
        today = datetime.now(tz=UTC).date()

        comparison_entries: list[FighterComparisonEntry] = []
        for fighter in fighters:
            resolve_fighter_image(fighter.id, fighter.image_url)
            fighter_stats = stats_map.get(fighter.id, {})
            comparison_entries.append(
                FighterComparisonEntry(
                    fighter_id=fighter.id,
                    name=fighter.name,
                    record=fighter.record,
                    division=fighter.division,
                    age=_calculate_age(dob=fighter.dob, reference_date=today),
                    striking=fighter_stats.get("striking", {}),
                    grappling=fighter_stats.get("grappling", {}),
                    significant_strikes=fighter_stats.get("significant_strikes", {}),
                    takedown_stats=fighter_stats.get("takedown_stats", {}),
                    career=fighter_stats.get("career", {}),
                    is_current_champion=fighter.is_current_champion,
                    is_former_champion=fighter.is_former_champion,
                    was_interim=bool(getattr(fighter, "was_interim", False)),
                )
            )

        return comparison_entries

    async def get_random_fighter(self) -> FighterListItem | None:
        """Return a single random fighter list item or ``None`` when empty."""

        fighter = await self._repository.get_random_fighter()
        if fighter is None:
            return None

        ranking = (await self._repository.get_ranking_summaries([fighter.id])).get(
            fighter.id
        )
        status_map = (await self._repository.get_fight_status([fighter.id])).get(
            fighter.id, {}
        )
        today = datetime.now(tz=UTC).date()
        return self._build_list_item(
            fighter,
            include_streak=False,
            today=today,
            ranking=ranking,
            fight_status=status_map,
            streak_data=None,
        )

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
        """Delegate to the repository for roster counts with location filters."""

        return await self._repository.count_fighters(
            nationality=nationality,
            birthplace_country=birthplace_country,
            birthplace_city=birthplace_city,
            training_country=training_country,
            training_city=training_city,
            training_gym=training_gym,
            has_location_data=has_location_data,
        )

    def _build_list_item(
        self,
        fighter: Fighter,
        *,
        include_streak: bool,
        today: date,
        ranking: FighterRankingSummary | None,
        fight_status: Mapping[str, object] | None,
        streak_data: Mapping[str, object] | None,
    ) -> FighterListItem:
        """Compose a :class:`FighterListItem` from raw fighter data."""

        streak_type: Literal["win", "loss", "draw", "none"] = "none"
        streak_count = 0
        if include_streak:
            raw_type = cast(
                str | None,
                (streak_data or {}).get("current_streak_type"),
            ) or cast(str | None, fighter.current_streak_type)
            if raw_type:
                normalized = raw_type.strip().lower()
                if normalized in {"win", "loss", "draw", "none"}:
                    streak_type = cast(
                        Literal["win", "loss", "draw", "none"], normalized
                    )
            streak_count = int((streak_data or {}).get("current_streak_count") or 0)
            if streak_count <= 0:
                streak_type = "none"

        next_fight_date = None
        last_fight_result: Literal["win", "loss", "draw", "nc"] | None = None
        if fight_status:
            next_fight_date = cast(date | None, fight_status.get("next_fight_date"))
            last_value = fight_status.get("last_fight_result")
            if isinstance(last_value, str):
                normalized_last = last_value.strip().lower()
                if normalized_last in {"win", "loss", "draw", "nc"}:
                    last_fight_result = cast(
                        Literal["win", "loss", "draw", "nc"], normalized_last
                    )
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
            age=_calculate_age(dob=fighter.dob, reference_date=today),
            is_current_champion=fighter.is_current_champion,
            is_former_champion=fighter.is_former_champion,
            was_interim=bool(getattr(fighter, "was_interim", False)),
            current_streak_type=streak_type,
            current_streak_count=streak_count,
            current_rank=ranking.current_rank if ranking else None,
            current_rank_source=ranking.current_rank_source if ranking else None,
            current_rank_division=ranking.current_rank_division if ranking else None,
            current_rank_date=ranking.current_rank_date if ranking else None,
            peak_rank=ranking.peak_rank if ranking else None,
            peak_rank_source=ranking.peak_rank_source if ranking else None,
            peak_rank_division=ranking.peak_rank_division if ranking else None,
            peak_rank_date=ranking.peak_rank_date if ranking else None,
            birthplace=fighter.birthplace,
            birthplace_city=fighter.birthplace_city,
            birthplace_country=fighter.birthplace_country,
            nationality=fighter.nationality,
            fighting_out_of=fighter.fighting_out_of,
            training_gym=fighter.training_gym,
            training_city=fighter.training_city,
            training_country=fighter.training_country,
            next_fight_date=next_fight_date,
            last_fight_date=fighter.last_fight_date,
            last_fight_result=last_fight_result,
        )

    def _collect_opponent_ids(self, fights: Sequence[FighterFightRow]) -> list[str]:
        """Return unique opponent identifiers encountered in ``fights``."""

        opponent_ids: list[str] = []
        for row in fights:
            candidate = row.opponent_id if row.is_primary else row.inverted_opponent_id
            if candidate and candidate not in opponent_ids:
                opponent_ids.append(candidate)
        return opponent_ids

    def _build_fight_history(
        self,
        fights: Sequence[FighterFightRow],
        opponent_names: Mapping[str, str],
    ) -> list[FightHistoryEntry]:
        """Convert raw fight rows into deduplicated, chronologically sorted entries."""

        fight_lookup: dict[tuple[str, date | None, str], FightHistoryEntry] = {}
        for row in fights:
            if row.is_primary:
                opponent_id = row.opponent_id
                opponent_name = row.opponent_name or opponent_names.get(
                    opponent_id or "", "Unknown"
                )
                normalized_result = row.result or ""
            else:
                opponent_id = row.inverted_opponent_id
                opponent_name = opponent_names.get(opponent_id or "", "Unknown")
                normalized_result = _invert_fight_result(row.result)

            fight_key = create_fight_key(
                row.event_name,
                row.event_date,
                opponent_id,
                opponent_name,
            )

            new_entry = FightHistoryEntry(
                fight_id=row.fight_id,
                event_name=row.event_name,
                event_date=row.event_date,
                opponent=opponent_name,
                opponent_id=opponent_id,
                result=normalized_result,
                method=(row.method or ""),
                round=row.round,
                time=row.time,
                fight_card_url=row.fight_card_url,
                stats=row.stats or {},
            )

            existing = fight_lookup.get(fight_key)
            if existing is None or should_replace_fight(
                existing.result, normalized_result
            ):
                fight_lookup[fight_key] = new_entry

        fight_history = list(fight_lookup.values())
        return sort_fight_history(fight_history)


__all__ = ["FighterPresentationService"]
