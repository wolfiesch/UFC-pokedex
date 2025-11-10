from __future__ import annotations

import asyncio
import logging
import secrets
from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime
import time
from typing import Any, Literal, Protocol, runtime_checkable

from fastapi import Depends
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache import (
    CacheClient,
    comparison_key,
    detail_key,
    get_cache_client,
    graph_key,
    list_key,
    search_key,
)
from backend.db.connection import get_db
from backend.db.repositories import PostgreSQLFighterRepository
from backend.db.repositories.fighter_repository import (
    FighterSearchFilters,
    filter_roster_entries,
    normalize_search_filters,
    paginate_roster_entries,
)
from backend.schemas.fight_graph import (
    FightGraphLink,
    FightGraphNode,
    FightGraphResponse,
)
from backend.schemas.fighter import (
    FighterComparisonEntry,
    FighterDetail,
    FighterListItem,
    PaginatedFightersResponse,
)
from backend.schemas.stats import (
    LeaderboardDefinition,
    LeaderboardMetricId,
    LeaderboardsResponse,
    StatsSummaryMetric,
    StatsSummaryResponse,
    TrendTimeBucket,
    TrendsResponse,
)

logger = logging.getLogger(__name__)

_LOCAL_CACHE_DEFAULT_TTL = 300
_local_cache: dict[str, tuple[float, Any]] = {}
_local_cache_lock = asyncio.Lock()


async def _local_cache_get(key: str) -> Any | None:
    """Return cached value from the in-process cache if it is still fresh."""
    async with _local_cache_lock:
        entry = _local_cache.get(key)
        if entry is None:
            return None

        expires_at, value = entry
        if expires_at < time.time():
            _local_cache.pop(key, None)
            return None
        return value


async def _local_cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    """Store value in the in-process cache with a TTL."""
    ttl_seconds = ttl if ttl is not None and ttl > 0 else _LOCAL_CACHE_DEFAULT_TTL
    async with _local_cache_lock:
        _local_cache[key] = (time.time() + ttl_seconds, value)


@runtime_checkable
class FighterRepositoryProtocol(Protocol):
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
        accuracy_metric: LeaderboardMetricId,
        submissions_metric: LeaderboardMetricId,
        start_date: date | None,
        end_date: date | None,
    ) -> LeaderboardsResponse:
        """Generate leaderboard slices for accuracy- and submission-oriented metrics."""

    async def get_trends(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        time_bucket: TrendTimeBucket,
        streak_limit: int,
    ) -> TrendsResponse:
        """Summarize longitudinal streaks and fight duration trends within the roster."""

    async def search_fighters(
        self,
        query: str | None = None,
        stance: str | None = None,
        division: str | None = None,
        champion_statuses: list[str] | None = None,
        streak_type: Literal["win", "loss", "draw", "none"] | None = None,
        min_streak_count: int | None = None,
        include_streak: bool = False,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[list[FighterListItem], int]:
        """Search roster entries using optional fighter metadata filters."""

    async def get_fighters_for_comparison(
        self, fighter_ids: Sequence[str]
    ) -> list[FighterComparisonEntry]:
        """Return stat snapshots for the provided fighter identifiers."""

    async def count_fighters(self) -> int:
        """Return the total number of indexed fighters."""

    async def get_random_fighter(self) -> FighterListItem | None:
        """Return a random fighter suitable for roster teasers."""

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
        include_streak: bool = False,
        streak_window: int = 6,
    ) -> Iterable[FighterListItem]:
        """Return fighters in insertion order while honoring pagination hints."""

        roster: list[FighterListItem] = [
            self._list_item_from_detail(detail) for detail in self._fighters.values()
        ]
        return paginate_roster_entries(
            roster,
            limit=limit,
            offset=offset,
        )

    async def get_fighter(self, fighter_id: str) -> FighterDetail | None:
        return self._fighters.get(fighter_id)

    async def stats_summary(self) -> StatsSummaryResponse:
        return StatsSummaryResponse(
            metrics=[
                StatsSummaryMetric(
                    id="fighters_indexed",
                    label="Fighters Indexed",
                    value=float(len(self._fighters)),
                    description="Prototype repository fighter count.",
                )
            ]
        )

    async def get_leaderboards(
        self,
        *,
        limit: int,
        accuracy_metric: LeaderboardMetricId,
        submissions_metric: LeaderboardMetricId,
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
        time_bucket: TrendTimeBucket,
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
    ) -> tuple[list[FighterListItem], int]:
        """Filter in-memory fighters using roster-style constraints."""

        roster: list[FighterListItem] = [
            self._list_item_from_detail(detail) for detail in self._fighters.values()
        ]
        filters: FighterSearchFilters = normalize_search_filters(
            query=query,
            stance=stance,
            division=division,
            champion_statuses=champion_statuses,
            streak_type=streak_type,
            min_streak_count=min_streak_count,
        )
        filtered = filter_roster_entries(
            roster,
            filters=filters,
        )
        total = len(filtered)
        paginated = paginate_roster_entries(
            filtered,
            limit=limit,
            offset=offset,
        )
        return paginated, total

    async def count_fighters(self) -> int:
        """Return the total number of in-memory fighters."""

        return len(self._fighters)

    async def get_random_fighter(self) -> FighterListItem | None:
        """Return a random fighter from the in-memory store."""

        if not self._fighters:
            return None
        return self._list_item_from_detail(
            secrets.choice(list(self._fighters.values()))
        )


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


class FighterService:
    def __init__(
        self,
        repository: FighterRepositoryProtocol | PostgreSQLFighterRepository,
        cache: CacheClient | None = None,
    ) -> None:
        self._repository = repository
        self._cache = cache

    async def _cache_get(self, key: str) -> Any:
        cached: Any | None = None
        if self._cache is not None:
            cached = await self._cache.get_json(key)
        if cached is not None:
            return cached
        return await _local_cache_get(key)

    async def _cache_set(self, key: str, value: Any, ttl: int | None = None) -> None:
        if self._cache is not None:
            await self._cache.set_json(key, value, ttl=ttl)
        if value is not None:
            await _local_cache_set(key, value, ttl=ttl)

    async def list_fighters(
        self,
        limit: int | None = None,
        offset: int | None = None,
        *,
        include_streak: bool = False,
        streak_window: int = 6,
    ) -> list[FighterListItem]:
        """Return paginated fighter summaries from the backing repository."""

        # Cache paginated responses (including streak variants) using a key that
        # incorporates pagination and streak options so variants remain isolated.
        use_cache = (
            limit is not None and offset is not None and limit >= 0 and offset >= 0
        )
        cache_key = (
            list_key(
                limit,
                offset,
                include_streak=include_streak,
                streak_window=streak_window,
            )
            if use_cache
            else None
        )

        if use_cache and cache_key is not None:
            cached = await self._cache_get(cache_key)
            if isinstance(cached, list):
                try:
                    return [FighterListItem.model_validate(item) for item in cached]
                except ValidationError as exc:  # pragma: no cover - defensive fallback
                    logger.warning(
                        "Failed to deserialize cached fighter list for key %s: %s",
                        cache_key,
                        exc,
                    )

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
            except ValidationError as exc:  # pragma: no cover - defensive fallback
                logger.warning(
                    "Failed to deserialize cached fighter detail for key %s: %s",
                    cache_key,
                    exc,
                )

        fighter = await self._repository.get_fighter(fighter_id)
        if fighter:
            # Fighter detail (bio rarely changes) - cache for 2 hours
            await self._cache_set(cache_key, fighter.model_dump(), ttl=7200)
        return fighter

    async def get_stats_summary(self) -> StatsSummaryResponse:
        """Expose system-level counts such as fighters indexed for dashboards."""
        cache_key = "stats:summary"

        cached = await self._cache_get(cache_key)
        if isinstance(cached, dict):
            try:
                return StatsSummaryResponse.model_validate(cached)
            except ValidationError as exc:  # pragma: no cover - defensive fallback
                logger.warning(
                    "Failed to deserialize cached stats summary for key %s: %s",
                    cache_key,
                    exc,
                )

        summary = await self._repository.stats_summary()
        await self._cache_set(cache_key, summary.model_dump(mode="json"), ttl=300)
        return summary

    async def count_fighters(self) -> int:
        """Get the total count of fighters with caching."""
        cache_key = "fighters:count"

        # Try cache first
        cached = await self._cache_get(cache_key)
        if cached is not None:
            return int(cached)

        # Compute count from repository
        count = await self._repository.count_fighters()

        # Cache for 10 minutes (count rarely changes)
        await self._cache_set(cache_key, count, ttl=600)
        return count

    async def get_random_fighter(self) -> FighterListItem | None:
        """Get a random fighter."""
        return await self._repository.get_random_fighter()

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

        filters: FighterSearchFilters = normalize_search_filters(
            query=query,
            stance=stance,
            division=division,
            champion_statuses=champion_statuses,
            streak_type=streak_type,
            min_streak_count=min_streak_count,
        )

        use_cache = self._cache is not None and (
            filters.query
            or filters.stance
            or filters.division
            or filters.champion_statuses
            or filters.streak_type
        )
        cache_key = (
            search_key(
                query=filters.query or "",
                stance=filters.stance,
                division=filters.division,
                champion_statuses=(
                    ",".join(filters.champion_statuses)
                    if filters.champion_statuses
                    else None
                ),
                streak_type=filters.streak_type,
                min_streak_count=filters.min_streak_count,
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
                except ValidationError as exc:  # pragma: no cover
                    logger.warning(
                        "Failed to deserialize cached fighter search for key %s: %s",
                        cache_key,
                        exc,
                    )

        fighters, total = await self._repository.search_fighters(
            query=filters.query,
            stance=filters.stance,
            division=filters.division,
            champion_statuses=(
                list(filters.champion_statuses) if filters.champion_statuses else None
            ),
            streak_type=filters.streak_type,
            min_streak_count=filters.min_streak_count,
            include_streak=include_streak,
            limit=resolved_limit,
            offset=resolved_offset,
        )

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
                except ValidationError as exc:  # pragma: no cover
                    logger.warning(
                        "Failed to deserialize cached fighter comparison for key %s: %s",
                        cache_key,
                        exc,
                    )

        fighters = await self._repository.get_fighters_for_comparison(fighter_ids)

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
                except ValidationError as exc:  # pragma: no cover - defensive fallback
                    logger.warning(
                        "Failed to deserialize cached fight graph for key %s: %s",
                        cache_key,
                        exc,
                    )

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
        accuracy_metric: LeaderboardMetricId = "sig_strikes_accuracy_pct",
        submissions_metric: LeaderboardMetricId = "avg_submissions",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> LeaderboardsResponse:
        """Surface aggregated leaderboards for accuracy- and submission-based metrics."""

        cache_key = ":".join(
            [
                "stats",
                "leaderboards",
                str(limit),
                accuracy_metric,
                submissions_metric,
                start_date.isoformat() if start_date else "*",
                end_date.isoformat() if end_date else "*",
            ]
        )

        cached = await self._cache_get(cache_key)
        if isinstance(cached, dict):
            try:
                return LeaderboardsResponse.model_validate(cached)
            except ValidationError as exc:  # pragma: no cover - defensive fallback
                logger.warning(
                    "Failed to deserialize cached leaderboards for key %s: %s",
                    cache_key,
                    exc,
                )

        response = await self._repository.get_leaderboards(
            limit=limit,
            accuracy_metric=accuracy_metric,
            submissions_metric=submissions_metric,
            start_date=start_date,
            end_date=end_date,
        )

        await self._cache_set(
            cache_key,
            response.model_dump(mode="json"),
            ttl=180,
        )
        return response

    async def get_trends(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        time_bucket: TrendTimeBucket = "month",
        streak_limit: int = 5,
    ) -> TrendsResponse:
        """Provide historical streaks and fight duration trends for analytics dashboards."""

        cache_key = ":".join(
            [
                "stats",
                "trends",
                start_date.isoformat() if start_date else "*",
                end_date.isoformat() if end_date else "*",
                time_bucket,
                str(streak_limit),
            ]
        )

        cached = await self._cache_get(cache_key)
        if isinstance(cached, dict):
            try:
                return TrendsResponse.model_validate(cached)
            except ValidationError as exc:  # pragma: no cover - defensive fallback
                logger.warning(
                    "Failed to deserialize cached trends for key %s: %s",
                    cache_key,
                    exc,
                )

        response = await self._repository.get_trends(
            start_date=start_date,
            end_date=end_date,
            time_bucket=time_bucket,
            streak_limit=streak_limit,
        )

        await self._cache_set(
            cache_key,
            response.model_dump(mode="json"),
            ttl=180,
        )
        return response


async def get_fighter_service(
    session: AsyncSession = Depends(get_db),
    cache: CacheClient = Depends(get_cache_client),
) -> FighterService:
    """FastAPI dependency that wires the repository and cache layer."""

    repository = PostgreSQLFighterRepository(session)
    return FighterService(repository, cache=cache)
