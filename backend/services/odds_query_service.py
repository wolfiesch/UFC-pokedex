"""Service exposing betting odds read operations with caching."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel

from backend.cache import CacheClient
from backend.db.models import FighterOdds
from backend.db.repositories.odds import QUALITY_TIERS
from backend.schemas.odds import (
    ClosingRange,
    FighterOddsChartFight,
    FighterOddsChartResponse,
    FighterOddsHistoryEntry,
    FighterOddsHistoryResponse,
    FightOddsDetailResponse,
    OddsCoverageStats,
    OddsQualityStatsResponse,
    OddsTimeSeriesPoint,
)
from backend.services.caching import CacheableService, cached

logger = logging.getLogger(__name__)

FIGHTER_HISTORY_TTL = 300  # 5 minutes
FIGHTER_CHART_TTL = 600  # 10 minutes
FIGHT_DETAIL_TTL = 900  # 15 minutes
ODDS_STATS_TTL = 3600  # 1 hour


class InvalidQualityTierError(ValueError):
    """Raised when the caller passes an unknown quality tier filter."""


def _sanitize_datetime_string(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _normalize_quality_tier(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in QUALITY_TIERS:
        raise InvalidQualityTierError(
            f"quality_min must be one of {', '.join(QUALITY_TIERS)}"
        )
    return normalized


def _cache_quality_value(value: str | None) -> str | None:
    return value.strip().lower() if value else None


def _make_closing_range(row: FighterOdds) -> ClosingRange | None:
    start = row.closing_range_start
    end = row.closing_range_end
    if not start and not end:
        return None
    return ClosingRange(start=start, end=end or start)


def _normalize_time_series(history: Iterable[Any]) -> list[OddsTimeSeriesPoint]:
    points: list[OddsTimeSeriesPoint] = []
    for entry in history or []:
        odds_value = entry.get("odds")
        try:
            odds = float(odds_value)
        except (TypeError, ValueError):
            continue

        timestamp_ms = entry.get("timestamp_ms")
        timestamp_str = entry.get("timestamp")

        dt: datetime | None = None
        if timestamp_str:
            try:
                dt = _sanitize_datetime_string(timestamp_str)
                if timestamp_ms is None:
                    timestamp_ms = int(dt.timestamp() * 1000)
            except ValueError:
                dt = None
        if dt is None and timestamp_ms is not None:
            dt = datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=UTC)
        if dt is None or timestamp_ms is None:
            continue

        points.append(
            OddsTimeSeriesPoint(
                timestamp_ms=int(timestamp_ms),
                timestamp=dt,
                odds=odds,
            )
        )

    points.sort(key=lambda point: point.timestamp_ms)
    return points


def _serialize_model(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")


def _deserialize_history(payload: dict[str, Any]) -> FighterOddsHistoryResponse:
    return FighterOddsHistoryResponse(**payload)


def _deserialize_chart(payload: dict[str, Any]) -> FighterOddsChartResponse:
    return FighterOddsChartResponse(**payload)


def _deserialize_detail(payload: dict[str, Any]) -> FightOddsDetailResponse:
    return FightOddsDetailResponse(**payload)


def _deserialize_stats(payload: dict[str, Any]) -> OddsQualityStatsResponse:
    return OddsQualityStatsResponse(**payload)


def _history_cache_key(fighter_id: str, limit: int, min_quality: str | None) -> str:
    # [*TO-DO*] - Cache key normalization: Empty string "" should not collide with None
    # Current: both None and "" become "all", causing potential cache pollution
    # Fix: quality_part = _cache_quality_value(min_quality) or "all"
    quality_part = min_quality or "all"
    return f"odds:fighter:{fighter_id}:history:{limit}:{quality_part}"


def _chart_cache_key(fighter_id: str, limit: int) -> str:
    return f"odds:fighter:{fighter_id}:chart:{limit}"


def _fight_cache_key(odds_id: str) -> str:
    return f"odds:fight:{odds_id}"


def _stats_cache_key() -> str:
    return "odds:stats:quality"


class OddsRepositoryProtocol(Protocol):
    async def fighter_exists(self, fighter_id: str) -> bool: ...

    async def count_fighter_odds(
        self, fighter_id: str, *, min_quality: str | None = None
    ) -> int: ...

    async def list_fighter_odds(
        self,
        fighter_id: str,
        *,
        limit: int | None = None,
        min_quality: str | None = None,
    ) -> list[FighterOdds]: ...

    async def get_odds_by_id(self, odds_id: str) -> FighterOdds | None: ...

    async def get_quality_stats(self) -> dict[str, Any]: ...


class OddsQueryService(CacheableService):
    """High-level odds read service with cache-friendly responses."""

    def __init__(
        self,
        repository: OddsRepositoryProtocol,
        *,
        cache: CacheClient | None = None,
    ) -> None:
        super().__init__(cache=cache)
        self._repository = repository

    @cached(
        lambda _self, fighter_id, *, limit=100, min_quality=None: _history_cache_key(
            fighter_id, limit, _cache_quality_value(min_quality)
        ),
        ttl=FIGHTER_HISTORY_TTL,
        serializer=_serialize_model,
        deserializer=_deserialize_history,
        deserialize_error_message="Failed to deserialize fighter odds history {key}: {error}",
    )
    async def get_fighter_odds_history(
        self,
        fighter_id: str,
        *,
        limit: int = 100,
        min_quality: str | None = None,
    ) -> FighterOddsHistoryResponse | None:
        quality = _normalize_quality_tier(min_quality)
        exists = await self._repository.fighter_exists(fighter_id)
        if not exists:
            return None

        rows = await self._repository.list_fighter_odds(
            fighter_id, limit=limit, min_quality=quality
        )
        total = await self._repository.count_fighter_odds(
            fighter_id, min_quality=quality
        )
        entries = [
            FighterOddsHistoryEntry(
                id=row.id,
                opponent_name=row.opponent_name,
                event_name=row.event_name,
                event_date=row.event_date,
                event_url=row.event_url,
                opening_odds=row.opening_odds,
                closing_range=_make_closing_range(row),
                num_odds_points=row.num_odds_points,
                data_quality=row.data_quality_tier or "no_data",
            )
            for row in rows
        ]

        return FighterOddsHistoryResponse(
            fighter_id=fighter_id,
            total_fights=total,
            returned=len(entries),
            odds_history=entries,
        )

    @cached(
        lambda _self, fighter_id, *, limit=20: _chart_cache_key(fighter_id, limit),
        ttl=FIGHTER_CHART_TTL,
        serializer=_serialize_model,
        deserializer=_deserialize_chart,
        deserialize_error_message="Failed to deserialize fighter odds chart {key}: {error}",
    )
    async def get_fighter_odds_chart(
        self,
        fighter_id: str,
        *,
        limit: int = 20,
    ) -> FighterOddsChartResponse | None:
        exists = await self._repository.fighter_exists(fighter_id)
        if not exists:
            return None

        rows = await self._repository.list_fighter_odds(fighter_id, limit=limit)
        fights = [
            FighterOddsChartFight(
                fight_id=row.id,
                opponent=row.opponent_name,
                event=row.event_name,
                event_date=row.event_date,
                event_url=row.event_url,
                opening_odds=row.opening_odds,
                closing_odds=row.closing_range_end or row.closing_range_start,
                quality=row.data_quality_tier or "no_data",
                num_odds_points=row.num_odds_points,
                time_series=_normalize_time_series(row.mean_odds_history or []),
            )
            for row in rows
        ]

        return FighterOddsChartResponse(fighter_id=fighter_id, fights=fights)

    @cached(
        lambda _self, odds_id: _fight_cache_key(odds_id),
        ttl=FIGHT_DETAIL_TTL,
        serializer=_serialize_model,
        deserializer=_deserialize_detail,
        deserialize_error_message="Failed to deserialize fight odds detail {key}: {error}",
    )
    async def get_fight_odds_detail(self, odds_id: str) -> FightOddsDetailResponse | None:
        row = await self._repository.get_odds_by_id(odds_id)
        if row is None:
            return None

        return FightOddsDetailResponse(
            id=row.id,
            fighter_id=row.fighter_id,
            opponent_name=row.opponent_name,
            event_name=row.event_name,
            event_date=row.event_date,
            event_url=row.event_url,
            opening_odds=row.opening_odds,
            closing_range=_make_closing_range(row),
            mean_odds_history=_normalize_time_series(row.mean_odds_history or []),
            num_odds_points=row.num_odds_points,
            data_quality=row.data_quality_tier or "no_data",
            scraped_at=row.scraped_at,
            bfo_fighter_url=row.bfo_fighter_url,
        )

    @cached(
        lambda _self: _stats_cache_key(),
        ttl=ODDS_STATS_TTL,
        serializer=_serialize_model,
        deserializer=_deserialize_stats,
        deserialize_error_message="Failed to deserialize odds stats cache {key}: {error}",
    )
    async def get_quality_stats(self) -> OddsQualityStatsResponse:
        stats = await self._repository.get_quality_stats()
        coverage = stats["coverage"]
        quality_distribution = stats["quality_distribution"]
        return OddsQualityStatsResponse(
            total_records=stats["total_records"],
            unique_fighters=stats["unique_fighters"],
            avg_odds_points=stats["avg_odds_points"],
            quality_distribution=quality_distribution,
            coverage_stats=OddsCoverageStats(
                fighters_with_odds=coverage["fighters_with_odds"],
                total_fighters=coverage["total_fighters"],
                coverage_percentage=coverage["coverage_percentage"],
            ),
        )


__all__ = [
    "InvalidQualityTierError",
    "OddsQueryService",
    "OddsRepositoryProtocol",
]
