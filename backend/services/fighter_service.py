from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import date, datetime, timezone
from typing import Any, Literal

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import (
    CacheClient,
    comparison_key,
    graph_key,
    detail_key,
    get_cache_client,
    list_key,
    search_key,
)
from backend.db.connection import get_db
from backend.db.repositories import PostgreSQLFighterRepository
from backend.schemas.fighter import (
    FighterComparisonEntry,
    FighterDetail,
    FighterListItem,
    PaginatedFightersResponse,
)
from backend.schemas.fight_graph import (
    FightGraphLink,
    FightGraphNode,
    FightGraphResponse,
)
from backend.schemas.stats import (
    LeaderboardDefinition,
    LeaderboardsResponse,
    StatsSummaryResponse,
    TrendsResponse,
)


class FighterRepositoryProtocol:
    async def list_fighters(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        include_streak: bool = False,
        streak_window: int = 6,
    ) -> Iterable[FighterListItem]:
        """Return lightweight fighter listings honoring pagination hints."""

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Retrieve a single fighter with rich detail by unique identifier."""

    async def stats_summary(self) -> StatsSummaryResponse:
        """Provide high-level metrics describing the indexed roster."""

    async def get_leaderboards(
        self,
        *,
        limit: int,
        accuracy_metric: str,
        submissions_metric: str,
        start_date: date | None,
        end_date: date | None,
    ) -> LeaderboardsResponse:
        """Generate leaderboard slices for accuracy- and submission-oriented metrics."""

    async def get_trends(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        time_bucket: Literal["month", "quarter", "year"],
        streak_limit: int,
    ) -> TrendsResponse:
        """Summarize longitudinal streaks and fight duration trends within the roster."""

    async def get_fighters_for_comparison(
        self, fighter_ids: Sequence[str]
    ) -> list[FighterComparisonEntry]:
        """Return stat snapshots for the provided fighter identifiers."""

    async def get_fight_graph(
        self,
        *,
        division: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 200,
        include_upcoming: bool = False,
    ) -> FightGraphResponse:
        """Assemble a graph-friendly view of fighters and fight relationships."""


class InMemoryFighterRepository(FighterRepositoryProtocol):
    """Temporary repository used until database layer is implemented."""

    def __init__(self) -> None:
        self._fighters = {
            "sample-fighter": FighterDetail(
                fighter_id="sample-fighter",
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

    async def list_fighters(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        include_streak: bool = False,
        streak_window: int = 6,
    ) -> Iterable[FighterListItem]:
        """Return fighters in insertion order while honoring pagination hints."""

        fighters = list(self._fighters.values())
        start = 0 if offset is None or offset < 0 else offset
        if limit is None or limit < 0:
            return fighters[start:]
        return fighters[start : start + limit]

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        return self._fighters.get(fighter_id)

    async def stats_summary(self) -> dict[str, float]:
        return {"fighters_indexed": float(len(self._fighters))}

    async def get_leaderboards(
        self,
        *,
        limit: int,
        accuracy_metric: str,
        submissions_metric: str,
        start_date: date | None,
        end_date: date | None,
    ) -> LeaderboardsResponse:
        """Return empty leaderboard shells for the in-memory prototype repository."""

        placeholder_leaderboards: list[LeaderboardDefinition] = [
            LeaderboardDefinition(
                metric_id=accuracy_metric,
                title=f"{accuracy_metric.replace('_', ' ').title()} Leaderboard",
                description=(
                    "Placeholder leaderboard for accuracy-focused metrics while the "
                    "prototype repository lacks persistent data."
                ),
                entries=[],
            ),
            LeaderboardDefinition(
                metric_id=submissions_metric,
                title=f"{submissions_metric.replace('_', ' ').title()} Leaderboard",
                description=(
                    "Placeholder leaderboard for submission-focused metrics while the "
                    "prototype repository lacks persistent data."
                ),
                entries=[],
            ),
        ]

        return LeaderboardsResponse(leaderboards=placeholder_leaderboards)

    async def get_trends(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        time_bucket: Literal["month", "quarter", "year"],
        streak_limit: int,
    ) -> TrendsResponse:
        """Return empty trend payloads for the in-memory prototype repository."""

        return TrendsResponse()

    async def get_fighters_for_comparison(
        self, fighter_ids: Sequence[str]
    ) -> list[FighterComparisonEntry]:
        fighters: list[FighterComparisonEntry] = []
        for fighter_id in fighter_ids:
            detail = self._fighters.get(fighter_id)
            if detail is None:
                continue
            fighters.append(
                FighterComparisonEntry(
                    fighter_id=detail.fighter_id,
                    name=detail.name,
                    record=detail.record,
                    division=detail.division,
                    striking=detail.striking,
                    grappling=detail.grappling,
                    significant_strikes=detail.significant_strikes,
                    takedown_stats=detail.takedown_stats,
                    career={},
                )
            )
        return fighters

    async def get_fight_graph(
        self,
        *,
        division: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 200,
        include_upcoming: bool = False,
    ) -> FightGraphResponse:
        return FightGraphResponse()


def _calculate_network_density(node_count: int, link_count: int) -> float:
    """Return the density of an undirected fight graph."""

    if node_count <= 1:
        return 0.0
    max_edges = (node_count * (node_count - 1)) / 2
    if max_edges <= 0:
        return 0.0
    # Bound the ratio to avoid subtle floating point drift.
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
        metadata.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
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
    metadata.setdefault("generated_at", datetime.now(timezone.utc).isoformat())

    return FightGraphResponse(nodes=graph.nodes, links=graph.links, metadata=metadata)

    async def search_fighters(
        self,
        query: str | None = None,
        stance: str | None = None,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[list[FighterListItem], int]:
        fighters = list(self._fighters.values())
        query_lower = query.lower() if query else None
        stance_lower = stance.lower() if stance else None
        filtered: list[FighterListItem] = []
        for fighter in fighters:
            name_match = True
            if query_lower:
                name_parts = [fighter.name, fighter.nickname or ""]
                haystack = " ".join(part for part in name_parts if part).lower()
                name_match = query_lower in haystack
            stance_match = True
            if stance_lower:
                fighter_stance = (fighter.stance or "").lower()
                stance_match = fighter_stance == stance_lower
            if name_match and stance_match:
                filtered.append(fighter)

        total = len(filtered)
        start = offset or 0
        if start < 0:
            start = 0
        end = start + limit if limit is not None and limit > 0 else total
        return filtered[start:end], total


class FighterService:
    def __init__(
        self,
        repository: FighterRepositoryProtocol | PostgreSQLFighterRepository,
        cache: CacheClient | None = None,
    ) -> None:
        self._repository = repository
        self._cache = cache

    async def _cache_get(self, key: str) -> Any:
        if self._cache is None:
            return None
        return await self._cache.get_json(key)

    async def _cache_set(self, key: str, value: Any, ttl: int | None = None) -> None:
        if self._cache is None:
            return
        await self._cache.set_json(key, value, ttl=ttl)

    async def list_fighters(
        self,
        limit: int | None = None,
        offset: int | None = None,
        *,
        include_streak: bool = False,
        streak_window: int = 6,
    ) -> list[FighterListItem]:
        """Return paginated fighter summaries from the backing repository."""

        # Disable list cache when streaks are included to avoid mixing cached
        # payload variants. We could fold the flags into the cache key, but the
        # list cache primarily exists for the simple roster view.
        use_cache = (
            self._cache is not None
            and limit is not None
            and offset is not None
            and limit >= 0
            and offset >= 0
            and not include_streak
        )
        cache_key = list_key(limit, offset) if use_cache else None

        if use_cache and cache_key is not None:
            cached = await self._cache_get(cache_key)
            if isinstance(cached, list):
                try:
                    return [FighterListItem.model_validate(item) for item in cached]
                except Exception:  # pragma: no cover - defensive fallback
                    pass

        fighters = await self._repository.list_fighters(
            limit=limit,
            offset=offset,
            include_streak=include_streak,
            streak_window=streak_window,
        )
        fighter_list = list(fighters)

        if use_cache and cache_key is not None:
            await self._cache_set(
                cache_key,
                [fighter.model_dump() for fighter in fighter_list],
                ttl=300,
            )

        return fighter_list

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        """Fetch a single fighter profile including detailed statistics."""
        cache_key = detail_key(fighter_id)
        cached = await self._cache_get(cache_key)
        if isinstance(cached, dict):
            try:
                return FighterDetail.model_validate(cached)
            except Exception:  # pragma: no cover - defensive fallback
                pass

        fighter = await self._repository.get_fighter(fighter_id)
        if fighter:
            await self._cache_set(cache_key, fighter.model_dump(), ttl=600)
        return fighter

    async def get_stats_summary(self) -> StatsSummaryResponse:
        """Expose system-level counts such as fighters indexed for dashboards."""

        return await self._repository.stats_summary()

    async def count_fighters(self) -> int:
        """Get the total count of fighters."""
        if hasattr(self._repository, "count_fighters"):
            return await self._repository.count_fighters()
        else:
            # Fallback for repositories without count
            fighters = await self._repository.list_fighters()
            return len(list(fighters))

    async def get_random_fighter(self) -> FighterListItem | None:
        """Get a random fighter."""
        if hasattr(self._repository, "get_random_fighter"):
            return await self._repository.get_random_fighter()
        else:
            # Fallback for repositories without random
            import random

            fighters = await self._repository.list_fighters()
            fighter_list = list(fighters)
            if not fighter_list:
                return None
            return random.choice(fighter_list)

    async def search_fighters(
        self,
        query: str | None = None,
        stance: str | None = None,
        division: str | None = None,
        champion_statuses: list[str] | None = None,
        streak_type: Literal["win", "loss"] | None = None,
        min_streak_count: int | None = None,
        include_streak: bool = False,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> PaginatedFightersResponse:
        """Search fighters by name, stance, division, champion status, or streak with pagination."""

        resolved_limit = limit if limit is not None and limit > 0 else 20
        resolved_offset = offset if offset is not None and offset >= 0 else 0

        normalized_query = (query or "").strip()
        normalized_stance = (stance or "").strip()
        normalized_division = (division or "").strip()
        normalized_champion_statuses = champion_statuses if champion_statuses else None

        query_param = normalized_query or None
        stance_param = normalized_stance or None
        division_param = normalized_division or None
        champion_statuses_param = normalized_champion_statuses
        streak_type_param = streak_type
        min_streak_count_param = min_streak_count

        use_cache = self._cache is not None and (
            normalized_query or normalized_stance or normalized_division or normalized_champion_statuses or streak_type
        )
        cache_key = (
            search_key(
                query=normalized_query,
                stance=normalized_stance if normalized_stance else None,
                division=normalized_division if normalized_division else None,
                champion_statuses=",".join(sorted(normalized_champion_statuses))
                if normalized_champion_statuses
                else None,
                streak_type=streak_type if streak_type else None,
                min_streak_count=min_streak_count if min_streak_count is not None else None,
                limit=resolved_limit,
                offset=resolved_offset,
            )
            if use_cache
            else None
        )

        if cache_key is not None:
            cached = await self._cache_get(cache_key)
            if isinstance(cached, dict):
                try:
                    return PaginatedFightersResponse.model_validate(cached)
                except Exception:  # pragma: no cover
                    pass

        if hasattr(self._repository, "search_fighters"):
            fighters, total = await self._repository.search_fighters(
                query=query_param,
                stance=stance_param,
                division=division_param,
                champion_statuses=champion_statuses_param,
                streak_type=streak_type_param,
                min_streak_count=min_streak_count_param,
                include_streak=include_streak,
                limit=resolved_limit,
                offset=resolved_offset,
            )
        else:
            fighters_iterable = await self._repository.list_fighters(
                include_streak=include_streak
            )
            query_lower = query_param.lower() if query_param else None
            stance_lower = stance_param.lower() if stance_param else None
            division_lower = division_param.lower() if division_param else None
            filtered: list[FighterListItem] = []
            for fighter in fighters_iterable:
                name_match = True
                if query_lower:
                    name_parts = [
                        getattr(fighter, "name", "") or "",
                        getattr(fighter, "nickname", "") or "",
                    ]
                    haystack = " ".join(part for part in name_parts if part).lower()
                    name_match = query_lower in haystack
                stance_match = True
                if stance_lower:
                    fighter_stance = (getattr(fighter, "stance", None) or "").lower()
                    stance_match = fighter_stance == stance_lower
                division_match = True
                if division_lower:
                    fighter_division = (
                        getattr(fighter, "division", None) or ""
                    ).lower()
                    division_match = fighter_division == division_lower
                streak_match = True
                if streak_type_param and min_streak_count_param:
                    fighter_streak_type = getattr(fighter, "current_streak_type", None)
                    fighter_streak_count = getattr(fighter, "current_streak_count", 0) or 0
                    streak_match = (
                        fighter_streak_type == streak_type_param
                        and fighter_streak_count >= min_streak_count_param
                    )
                if name_match and stance_match and division_match and streak_match:
                    filtered.append(fighter)

            total = len(filtered)
            end_index = resolved_offset + resolved_limit
            fighters = filtered[resolved_offset:end_index]

        has_more = resolved_offset + len(fighters) < total
        response = PaginatedFightersResponse(
            fighters=fighters,
            total=total,
            limit=resolved_limit,
            offset=resolved_offset,
            has_more=has_more,
        )

        if cache_key is not None:
            await self._cache_set(cache_key, response.model_dump(), ttl=300)

        return response

    async def compare_fighters(
        self, fighter_ids: Sequence[str]
    ) -> list[FighterComparisonEntry]:
        """Retrieve comparable stat bundles for the requested fighters."""

        use_cache = self._cache is not None and len(fighter_ids) >= 2
        cache_key = comparison_key(fighter_ids) if use_cache else None

        if cache_key is not None:
            cached = await self._cache_get(cache_key)
            if isinstance(cached, list):
                try:
                    return [
                        FighterComparisonEntry.model_validate(item) for item in cached
                    ]
                except Exception:  # pragma: no cover
                    pass

        if hasattr(self._repository, "get_fighters_for_comparison"):
            fighters = await self._repository.get_fighters_for_comparison(fighter_ids)
        else:
            fighters = []
            for fighter_id in fighter_ids:
                detail = await self._repository.get_fighter(fighter_id)
                if detail is None:
                    continue
                fighters.append(
                    FighterComparisonEntry(
                        fighter_id=detail.fighter_id,
                        name=detail.name,
                        record=detail.record,
                        division=detail.division,
                        striking=detail.striking,
                        grappling=detail.grappling,
                        significant_strikes=detail.significant_strikes,
                        takedown_stats=detail.takedown_stats,
                        career=getattr(detail, "career", {}),
                    )
                )

        if cache_key is not None and fighters:
            await self._cache_set(
                cache_key,
                [entry.model_dump() for entry in fighters],
                ttl=600,
            )

        return fighters

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

        cache_key: str | None = None
        if self._cache is not None:
            cache_key = graph_key(
                division=division,
                start_year=start_year,
                end_year=end_year,
                limit=limit,
                include_upcoming=include_upcoming,
            )
            cached = await self._cache_get(cache_key)
            if isinstance(cached, dict):
                try:
                    return FightGraphResponse.model_validate(cached)
                except Exception:  # pragma: no cover - defensive fallback
                    pass

        repository_method = getattr(self._repository, "get_fight_graph", None)
        if repository_method is None:
            return FightGraphResponse()

        raw_graph: FightGraphResponse = await repository_method(
            division=division,
            start_year=start_year,
            end_year=end_year,
            limit=limit,
            include_upcoming=include_upcoming,
        )

        graph = _augment_fight_graph_metadata(raw_graph)

        if cache_key is not None and graph.nodes:
            await self._cache_set(
                cache_key,
                graph.model_dump(mode="json"),
                ttl=300,
            )

        return graph

    async def get_leaderboards(
        self,
        *,
        limit: int = 10,
        accuracy_metric: str = "sig_strikes_accuracy_pct",
        submissions_metric: str = "avg_submissions",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> LeaderboardsResponse:
        """Surface aggregated leaderboards for accuracy- and submission-based metrics."""

        return await self._repository.get_leaderboards(
            limit=limit,
            accuracy_metric=accuracy_metric,
            submissions_metric=submissions_metric,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_trends(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        time_bucket: Literal["month", "quarter", "year"] = "month",
        streak_limit: int = 5,
    ) -> TrendsResponse:
        """Provide historical streaks and fight duration trends for analytics dashboards."""

        return await self._repository.get_trends(
            start_date=start_date,
            end_date=end_date,
            time_bucket=time_bucket,
            streak_limit=streak_limit,
        )


async def get_fighter_service(
    session: AsyncSession = Depends(get_db),
    cache: CacheClient = Depends(get_cache_client),
) -> FighterService:
    """FastAPI dependency that wires the repository and cache layer."""

    repository = PostgreSQLFighterRepository(session)
    return FighterService(repository, cache=cache)
