"""Service responsible for aggregating and caching fight graph payloads."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import CacheClient, get_cache_client, graph_key
from backend.db.connection import get_db
from backend.db.repositories.fight_graph_repository import FightGraphRepository
from backend.schemas.fight_graph import (
    FightGraphLink,
    FightGraphNode,
    FightGraphResponse,
)
from backend.services.caching import CacheableService, cached

logger = logging.getLogger(__name__)


def _calculate_network_density(node_count: int, link_count: int) -> float:
    """Return the graph density (0-1) capped to four decimal places."""

    if node_count <= 1:
        return 0.0
    max_edges = (node_count * (node_count - 1)) / 2
    if max_edges <= 0:
        return 0.0
    return round(min(1.0, max(0.0, link_count / max_edges)), 4)


def _derive_division_breakdown(nodes: list[FightGraphNode]) -> list[dict[str, Any]]:
    """Aggregate fighters per division for quick client legends."""

    counter: Counter[str] = Counter()
    for node in nodes:
        division = (node.division or "Unknown").strip() or "Unknown"
        counter[division] += 1

    total = sum(counter.values()) or 1
    breakdown: list[dict[str, Any]] = []
    for division, count in counter.most_common():
        breakdown.append(
            {
                "division": division,
                "count": count,
                "percentage": round((count / total) * 100, 1),
            }
        )
    return breakdown


def _derive_degree_map(links: list[FightGraphLink]) -> dict[str, int]:
    """Return a mapping of fighter IDs to their degree within the graph."""

    degree_map: dict[str, int] = {}
    for link in links:
        degree_map[link.source] = degree_map.get(link.source, 0) + 1
        degree_map[link.target] = degree_map.get(link.target, 0) + 1
    return degree_map


def _top_rivalries(
    links: list[FightGraphLink],
    nodes_by_id: dict[str, FightGraphNode],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Identify the busiest rivalries present in the fight graph."""

    if not links:
        return []

    sorted_links = sorted(links, key=lambda link: link.fights, reverse=True)
    rivalries: list[dict[str, Any]] = []
    for link in sorted_links[:limit]:
        source = nodes_by_id.get(link.source)
        target = nodes_by_id.get(link.target)
        rivalries.append(
            {
                "source": link.source,
                "target": link.target,
                "fights": link.fights,
                "source_name": source.name if source else None,
                "target_name": target.name if target else None,
                "last_event_name": link.last_event_name,
                "last_event_date": link.last_event_date,
            }
        )
    return rivalries


def _augment_fight_graph_metadata(graph: FightGraphResponse) -> FightGraphResponse:
    """Attach derived insights to a fight graph response before caching."""

    if not graph.nodes:
        metadata = dict(graph.metadata)
        metadata.setdefault("insights", {})
        metadata.setdefault("generated_at", datetime.now(UTC).isoformat())
        return FightGraphResponse(
            nodes=graph.nodes, links=graph.links, metadata=metadata
        )

    nodes_by_id: dict[str, FightGraphNode] = {
        node.fighter_id: node for node in graph.nodes
    }
    total_fights = sum(node.total_fights for node in graph.nodes)
    average_fights = round(total_fights / max(1, len(graph.nodes)), 2)
    density = _calculate_network_density(len(graph.nodes), len(graph.links))
    degree_map = _derive_degree_map(graph.links)

    top_hubs = sorted(
        (
            {
                "fighter_id": node.fighter_id,
                "name": node.name,
                "division": node.division,
                "total_fights": node.total_fights,
                "degree": degree_map.get(node.fighter_id, 0),
            }
            for node in graph.nodes
        ),
        key=lambda entry: (entry["total_fights"], entry["degree"]),
        reverse=True,
    )[:5]

    metadata = dict(graph.metadata)
    insights: dict[str, Any] = {
        "average_fights_per_fighter": average_fights,
        "network_density": density,
        "division_breakdown": _derive_division_breakdown(graph.nodes),
        "top_fighters": top_hubs,
        "busiest_rivalries": _top_rivalries(graph.links, nodes_by_id),
    }

    metadata["insights"] = insights
    metadata.setdefault("generated_at", datetime.now(UTC).isoformat())

    return FightGraphResponse(nodes=graph.nodes, links=graph.links, metadata=metadata)


def _fight_graph_cache_key(
    *,
    division: str | None,
    start_year: int | None,
    end_year: int | None,
    limit: int,
    include_upcoming: bool,
) -> str:
    """Return a deterministic cache key for fight graph aggregations."""

    return graph_key(
        division=division,
        start_year=start_year,
        end_year=end_year,
        limit=limit,
        include_upcoming=include_upcoming,
    )


class FightGraphService(CacheableService):
    """Service responsible for retrieving and augmenting fight graphs."""

    def __init__(
        self,
        repository: FightGraphRepository,
        *,
        cache: CacheClient | None = None,
    ) -> None:
        super().__init__(cache=cache)
        self._repository = repository

    @cached(
        lambda _self, *, division, start_year, end_year, limit, include_upcoming: _fight_graph_cache_key(
            division=division,
            start_year=start_year,
            end_year=end_year,
            limit=limit,
            include_upcoming=include_upcoming,
        ),
        ttl=300,
        serializer=lambda graph: graph.model_dump(mode="json"),
        deserializer=lambda payload: FightGraphResponse.model_validate(payload),
        deserialize_error_message=(
            "Failed to deserialize cached fight graph for key {key}: {error}"
        ),
    )
    async def get_fight_graph(
        self,
        *,
        division: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 200,
        include_upcoming: bool = False,
    ) -> FightGraphResponse:
        """Expose fight graph aggregation with lightweight caching."""

        raw_graph = await self._repository.get_fight_graph(
            division=division,
            start_year=start_year,
            end_year=end_year,
            limit=limit,
            include_upcoming=include_upcoming,
        )
        return _augment_fight_graph_metadata(raw_graph)


def get_fight_graph_service(
    session: AsyncSession = Depends(get_db),
    cache: CacheClient = Depends(get_cache_client),
) -> FightGraphService:
    """FastAPI dependency wiring the fight graph repository and cache."""

    repository = FightGraphRepository(session)
    return FightGraphService(repository, cache=cache)


__all__ = ["FightGraphService", "get_fight_graph_service"]
