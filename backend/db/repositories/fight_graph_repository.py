"""Fight graph repository for fight relationship visualization.

This repository handles:
- Building fight relationship graphs for visualization
- Aggregating fighter connections through fights
- Link deduplication and metadata
- Optimized for graph/network analysis workloads
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import desc, func, select

from backend.db.models import Fight, Fighter
from backend.db.repositories.base import (
    BaseRepository,
    _empty_breakdown,
    _normalize_result_category,
)
from backend.schemas.fight_graph import (
    FightGraphLink,
    FightGraphNode,
    FightGraphResponse,
)
from backend.services.image_resolver import resolve_fighter_image_cropped


class FightGraphRepository(BaseRepository):
    """Repository for fight relationship graph operations."""

    async def get_fight_graph(
        self,
        *,
        division: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 200,
        include_upcoming: bool = False,
    ) -> FightGraphResponse:
        """Aggregate fighters and bout links suitable for force-directed visualization."""

        if limit is not None and limit <= 0:
            return FightGraphResponse()

        fight_filters: list[Any] = []
        if start_year is not None:
            fight_filters.append(Fight.event_date >= date(start_year, 1, 1))
        if end_year is not None:
            fight_filters.append(Fight.event_date <= date(end_year, 12, 31))
        if not include_upcoming:
            fight_filters.append(func.lower(Fight.result) != "next")

        fight_count_expr = func.count().label("fight_count")
        latest_event_expr = func.max(Fight.event_date).label("latest_event_date")

        fight_counts_query = select(
            Fight.fighter_id, fight_count_expr, latest_event_expr
        ).join(Fighter, Fighter.id == Fight.fighter_id)
        if fight_filters:
            fight_counts_query = fight_counts_query.where(*fight_filters)
        if division:
            fight_counts_query = fight_counts_query.where(Fighter.division == division)
        fight_counts_query = fight_counts_query.group_by(Fight.fighter_id)
        fight_counts_query = fight_counts_query.order_by(desc(fight_count_expr))
        if limit is not None:
            fight_counts_query = fight_counts_query.limit(limit)

        fight_counts_result = await self._session.execute(fight_counts_query)
        fight_counts = fight_counts_result.all()

        id_order = [row.fighter_id for row in fight_counts]
        count_map = {row.fighter_id: int(row.fight_count or 0) for row in fight_counts}
        latest_map = {row.fighter_id: row.latest_event_date for row in fight_counts}

        if not id_order:
            fallback_query = (
                select(
                    Fighter.id,
                    Fighter.name,
                    Fighter.division,
                    Fighter.record,
                    Fighter.image_url,
                    Fighter.cropped_image_url,
                )
                .order_by(Fighter.name, Fighter.id)
            )
            if division:
                fallback_query = fallback_query.where(Fighter.division == division)
            if limit is not None:
                fallback_query = fallback_query.limit(limit)
            fallback_result = await self._session.execute(fallback_query)
            fallback_fighters = fallback_result.all()
            nodes = [
                FightGraphNode(
                    fighter_id=row.id,
                    name=row.name,
                    division=row.division,
                    record=row.record,
                    image_url=resolve_fighter_image_cropped(
                        row.id, row.image_url, row.cropped_image_url
                    ),
                    total_fights=0,
                    latest_event_date=None,
                )
                for row in fallback_fighters
            ]
            metadata = {
                "filters": {
                    "division": division,
                    "start_year": start_year,
                    "end_year": end_year,
                    "include_upcoming": include_upcoming,
                },
                "node_count": len(nodes),
                "link_count": 0,
                "limit": limit,
            }
            return FightGraphResponse(nodes=nodes, links=[], metadata=metadata)

        fighters_query = select(
            Fighter.id,
            Fighter.name,
            Fighter.division,
            Fighter.record,
            Fighter.image_url,
            Fighter.cropped_image_url,
        ).where(Fighter.id.in_(id_order))
        fighters_result = await self._session.execute(fighters_query)
        fighters = fighters_result.all()
        fighter_map = {row.id: row for row in fighters}

        nodes: list[FightGraphNode] = []
        for fighter_id in id_order:
            fighter_row = fighter_map.get(fighter_id)
            if fighter_row is None:
                continue
            nodes.append(
                FightGraphNode(
                    fighter_id=fighter_row.id,
                    name=fighter_row.name,
                    division=fighter_row.division,
                    record=fighter_row.record,
                    image_url=resolve_fighter_image_cropped(
                        fighter_row.id,
                        fighter_row.image_url,
                        fighter_row.cropped_image_url,
                    ),
                    total_fights=count_map.get(fighter_row.id, 0),
                    latest_event_date=latest_map.get(fighter_row.id),
                )
            )

        id_set = set(id_order)
        edges_filters = list(fight_filters)

        edges_query = select(Fight).where(
            Fight.fighter_id.in_(id_set),
            Fight.opponent_id.is_not(None),
            Fight.opponent_id.in_(id_set),
        )
        if edges_filters:
            edges_query = edges_query.where(*edges_filters)

        edges_result = await self._session.execute(edges_query)
        fights = edges_result.scalars().all()

        link_accumulator: dict[tuple[str, str], dict[str, Any]] = {}
        earliest_event: date | None = None
        latest_event: date | None = None
        for fight in fights:
            opponent_id = fight.opponent_id
            if opponent_id is None:
                continue

            pair = tuple(sorted((fight.fighter_id, opponent_id)))
            if pair[0] == pair[1]:
                continue

            entry = link_accumulator.setdefault(
                pair,
                {
                    "fights": 0,
                    "first_event_name": None,
                    "first_event_date": None,
                    "last_event_name": None,
                    "last_event_date": None,
                    "result_breakdown": {
                        pair[0]: _empty_breakdown(),
                        pair[1]: _empty_breakdown(),
                    },
                },
            )

            entry["fights"] += 1

            result_map = entry["result_breakdown"]
            if fight.fighter_id not in result_map:
                result_map[fight.fighter_id] = _empty_breakdown()

            normalized_result = _normalize_result_category(fight.result)
            if normalized_result not in result_map[fight.fighter_id]:
                result_map[fight.fighter_id][normalized_result] = 0
            result_map[fight.fighter_id][normalized_result] += 1

            other_id = pair[0] if fight.fighter_id == pair[1] else pair[1]
            if other_id not in result_map:
                result_map[other_id] = _empty_breakdown()

            if fight.event_date is not None:
                if earliest_event is None or fight.event_date < earliest_event:
                    earliest_event = fight.event_date
                if latest_event is None or fight.event_date > latest_event:
                    latest_event = fight.event_date

                last_date = entry["last_event_date"]
                if last_date is None or fight.event_date > last_date:
                    entry["last_event_date"] = fight.event_date
                    entry["last_event_name"] = fight.event_name
                first_date = entry["first_event_date"]
                if first_date is None or fight.event_date < first_date:
                    entry["first_event_date"] = fight.event_date
                    entry["first_event_name"] = fight.event_name
            elif entry["last_event_name"] is None:
                entry["last_event_name"] = fight.event_name
                if entry["first_event_name"] is None:
                    entry["first_event_name"] = fight.event_name

        links = [
            FightGraphLink(
                source=pair[0],
                target=pair[1],
                fights=data["fights"],
                first_event_name=data["first_event_name"],
                first_event_date=data["first_event_date"],
                last_event_name=data["last_event_name"],
                last_event_date=data["last_event_date"],
                result_breakdown=data["result_breakdown"],
            )
            for pair, data in link_accumulator.items()
        ]
        links.sort(key=lambda link: link.fights, reverse=True)

        metadata = {
            "filters": {
                "division": division,
                "start_year": start_year,
                "end_year": end_year,
                "include_upcoming": include_upcoming,
            },
            "node_count": len(nodes),
            "link_count": len(links),
            "limit": limit,
        }

        if earliest_event is not None or latest_event is not None:
            metadata["event_window"] = {
                "start": earliest_event,
                "end": latest_event,
            }

        return FightGraphResponse(nodes=nodes, links=links, metadata=metadata)
