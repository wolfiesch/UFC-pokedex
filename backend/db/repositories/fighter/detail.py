"""Detailed fighter retrieval helpers."""

from __future__ import annotations

import logging
import time
from datetime import UTC, date, datetime

from sqlalchemy import literal, select
from sqlalchemy.orm import load_only

from backend.db.models import Fight, Fighter
from backend.db.repositories.base import _calculate_age, _invert_fight_result
from backend.db.repositories.fight_utils import (
    compute_record_from_fights,
    create_fight_key,
    should_replace_fight,
    sort_fight_history,
)
from backend.schemas.fighter import FighterDetail, FightHistoryEntry
from backend.services.image_resolver import resolve_fighter_image

logger = logging.getLogger(__name__)


class FighterDetailMixin:
    """Provide a detail retrieval routine shared across repositories."""

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Return detailed fighter information via a single optimized query."""

        start_time = time.time()

        base_columns = self._fighter_detail_columns()
        load_columns, supports_was_interim = await self._resolve_fighter_columns(
            base_columns
        )
        fighter_query = (
            select(Fighter)
            .options(load_only(*load_columns))
            .where(Fighter.id == fighter_id)
        )
        fighter_result = await self._session.execute(fighter_query)
        fighter = fighter_result.scalar_one_or_none()

        if fighter is None:
            return None

        stats_map: dict[str, dict[str, str]] = {}

        primary_fights_cte = (
            select(
                Fight.id.label("fight_id"),
                Fight.event_name,
                Fight.event_date,
                Fight.opponent_id,
                Fight.opponent_name,
                Fight.result,
                Fight.method,
                Fight.round,
                Fight.time,
                Fight.fight_card_url,
                Fight.stats,
                literal(True).label("is_primary"),
                literal(None).label("inverted_opponent_id"),
            ).where(Fight.fighter_id == fighter_id)
        ).cte("primary_fights")

        opponent_fights_cte = (
            select(
                Fight.id.label("fight_id"),
                Fight.event_name,
                Fight.event_date,
                literal(None).label("opponent_id"),
                literal(None).label("opponent_name"),
                Fight.result,
                Fight.method,
                Fight.round,
                Fight.time,
                Fight.fight_card_url,
                Fight.stats,
                literal(False).label("is_primary"),
                Fight.fighter_id.label("inverted_opponent_id"),
            ).where(Fight.opponent_id == fighter_id)
        ).cte("opponent_fights")

        combined_query = select(primary_fights_cte).union_all(
            select(opponent_fights_cte)
        )

        all_fights_result = await self._session.execute(combined_query)
        all_fights_rows = all_fights_result.all()

        opponent_ids: set[str] = set()
        for row in all_fights_rows:
            if row.is_primary and row.opponent_id:
                opponent_ids.add(row.opponent_id)
            elif not row.is_primary and row.inverted_opponent_id:
                opponent_ids.add(row.inverted_opponent_id)

        opponent_lookup: dict[str, str] = {}
        if opponent_ids:
            opponent_rows = await self._session.execute(
                select(Fighter.id, Fighter.name).where(Fighter.id.in_(opponent_ids))
            )
            opponent_lookup = {row.id: row.name for row in opponent_rows.all()}

        fight_dict: dict[tuple[str, str | None, str], FightHistoryEntry] = {}

        for row in all_fights_rows:
            if row.is_primary:
                opponent_name = row.opponent_name or opponent_lookup.get(
                    row.opponent_id, "Unknown"
                )
                fight_key = create_fight_key(
                    row.event_name,
                    row.event_date,
                    row.opponent_id,
                    opponent_name,
                )

                new_entry = FightHistoryEntry(
                    fight_id=row.fight_id,
                    event_name=row.event_name,
                    event_date=row.event_date,
                    opponent=opponent_name,
                    opponent_id=row.opponent_id,
                    result=row.result,
                    method=row.method or "",
                    round=row.round,
                    time=row.time,
                    fight_card_url=row.fight_card_url,
                    stats=row.stats,
                )

                if fight_key not in fight_dict:
                    fight_dict[fight_key] = new_entry
                elif should_replace_fight(fight_dict[fight_key].result, row.result):
                    fight_dict[fight_key] = new_entry
            else:
                opponent_id = row.inverted_opponent_id
                opponent_name = opponent_lookup.get(opponent_id, "Unknown")

                fight_key = create_fight_key(
                    row.event_name, row.event_date, opponent_id, opponent_name
                )

                inverted_result = _invert_fight_result(row.result)

                new_entry = FightHistoryEntry(
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

                if fight_key not in fight_dict:
                    fight_dict[fight_key] = new_entry
                elif should_replace_fight(
                    fight_dict[fight_key].result, inverted_result
                ):
                    fight_dict[fight_key] = new_entry

        fight_history: list[FightHistoryEntry] = list(fight_dict.values())
        fight_history = sort_fight_history(fight_history)

        query_time = time.time() - start_time
        if query_time > 0.1:
            logger.warning("Slow fighter query: %s took %.3fs", fighter_id, query_time)

        computed_record = fighter.record or compute_record_from_fights(fight_history)

        today_utc: date = datetime.now(tz=UTC).date()
        fighter_age: int | None = _calculate_age(
            dob=fighter.dob,
            reference_date=today_utc,
        )

        summary = (await self._fetch_ranking_summaries([fighter.id])).get(fighter.id)

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
            current_rank=summary.current_rank if summary else None,
            current_rank_date=summary.current_rank_date if summary else None,
            current_rank_division=summary.current_rank_division if summary else None,
            current_rank_source=summary.current_rank_source if summary else None,
            peak_rank=summary.peak_rank if summary else None,
            peak_rank_date=summary.peak_rank_date if summary else None,
            peak_rank_division=summary.peak_rank_division if summary else None,
            peak_rank_source=summary.peak_rank_source if summary else None,
            birthplace=fighter.birthplace,
            birthplace_city=fighter.birthplace_city,
            birthplace_country=fighter.birthplace_country,
            nationality=fighter.nationality,
            fighting_out_of=fighter.fighting_out_of,
            training_gym=fighter.training_gym,
            training_city=fighter.training_city,
            training_country=fighter.training_country,
        )
