"""Analytics helpers for favorites collections."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence

from backend.db.models import (
    FavoriteCollection,
    FavoriteEntry as FavoriteEntryModel,
    Fight,
    Fighter,
)
from backend.schemas.favorites import (
    FavoriteActivityItem,
    FavoriteCollectionDetail,
    FavoriteCollectionStats,
    FavoriteCollectionSummary,
    FavoriteEntry as FavoriteEntrySchema,
    FavoriteUpcomingFight,
)


class FavoritesAnalytics:
    """Pure analytics routines decoupled from persistence and caching layers."""

    def collection_summary(
        self,
        collection: FavoriteCollection,
        *,
        stats: FavoriteCollectionStats | None,
    ) -> FavoriteCollectionSummary:
        """Build a lightweight summary payload for list responses."""

        return FavoriteCollectionSummary(
            id=collection.id,
            user_id=collection.user_id,
            title=collection.title,
            description=collection.description,
            is_public=collection.is_public,
            slug=collection.slug,
            metadata=collection.metadata_json or {},
            created_at=collection.created_at,
            updated_at=collection.updated_at,
            stats=stats,
        )

    def collection_detail(
        self,
        collection: FavoriteCollection,
        *,
        stats: FavoriteCollectionStats,
        entries: Sequence[FavoriteEntrySchema],
        activity: Sequence[FavoriteActivityItem],
    ) -> FavoriteCollectionDetail:
        """Build a fully hydrated detail payload."""

        return FavoriteCollectionDetail(
            id=collection.id,
            user_id=collection.user_id,
            title=collection.title,
            description=collection.description,
            is_public=collection.is_public,
            slug=collection.slug,
            metadata=collection.metadata_json or {},
            created_at=collection.created_at,
            updated_at=collection.updated_at,
            stats=stats,
            entries=list(entries),
            activity=list(activity),
        )

    def sort_entries(
        self, entries: Iterable[FavoriteEntryModel]
    ) -> list[FavoriteEntryModel]:
        """Return entries ordered by their persisted position."""

        return sorted(entries, key=lambda entry: entry.position)

    def entry_to_schema(self, entry: FavoriteEntryModel) -> FavoriteEntrySchema:
        """Convert a single ORM entry into its Pydantic representation."""

        return FavoriteEntrySchema(
            id=entry.id,
            fighter_id=entry.fighter_id,
            position=entry.position,
            notes=entry.notes,
            tags=list(entry.tags or []),
            metadata=entry.metadata_json or {},
            created_at=entry.added_at,
            updated_at=entry.updated_at,
        )

    def entries_to_schema(
        self, entries: Iterable[FavoriteEntryModel]
    ) -> list[FavoriteEntrySchema]:
        """Convert ORM entries into API schemas."""
        return [self.entry_to_schema(entry) for entry in self.sort_entries(entries)]

    def build_activity(
        self, entries: Iterable[FavoriteEntryModel]
    ) -> list[FavoriteActivityItem]:
        """Generate a simple activity feed from entry timestamps."""

        feed: list[FavoriteActivityItem] = []
        for entry in sorted(entries, key=lambda item: item.updated_at, reverse=True):
            action = (
                "updated"
                if entry.updated_at and entry.updated_at > entry.added_at
                else "added"
            )
            metadata: dict[str, object] = {}
            if entry.notes:
                metadata["notes"] = entry.notes
            if entry.tags:
                metadata["tags"] = entry.tags
            feed.append(
                FavoriteActivityItem(
                    entry_id=entry.id,
                    fighter_id=entry.fighter_id,
                    action=action,
                    occurred_at=(
                        entry.updated_at if action == "updated" else entry.added_at
                    ),
                    metadata=metadata,
                )
            )
        return feed

    def compute_collection_stats(
        self,
        *,
        entries: Iterable[FavoriteEntryModel],
        fights: Iterable[Fight],
    ) -> FavoriteCollectionStats:
        """Derive stats for a collection purely from entry and fight data."""

        entry_list = list(entries)
        if not entry_list:
            return FavoriteCollectionStats(
                total_fighters=0,
                win_rate=0.0,
                result_breakdown=self._empty_breakdown(),
                divisions=[],
                upcoming_fights=[],
            )

        breakdown = Counter(self._normalize_result(fight.result) for fight in fights)
        normalized = self._empty_breakdown()
        normalized.update(breakdown)

        wins = normalized.get("win", 0)
        losses = normalized.get("loss", 0)
        win_rate = wins / (wins + losses) if (wins + losses) else 0.0

        divisions = sorted(
            {
                entry.fighter.division
                for entry in entry_list
                if isinstance(entry.fighter, Fighter) and entry.fighter.division
            }
        )

        upcoming = [
            FavoriteUpcomingFight(
                fighter_id=fight.fighter_id,
                opponent_name=fight.opponent_name,
                event_name=fight.event_name,
                event_date=fight.event_date,
                weight_class=fight.weight_class,
            )
            for fight in fights
            if self._normalize_result(fight.result) == "upcoming"
        ]

        return FavoriteCollectionStats(
            total_fighters=len(entry_list),
            win_rate=win_rate,
            result_breakdown=normalized,
            divisions=divisions,
            upcoming_fights=upcoming,
        )

    def _empty_breakdown(self) -> dict[str, int]:
        """Provide default buckets for fight result categories."""

        return {"win": 0, "loss": 0, "draw": 0, "nc": 0, "upcoming": 0, "other": 0}

    def _normalize_result(self, result: str | None) -> str:
        """Normalize fight results to a handful of canonical buckets."""

        if result is None:
            return "other"
        normalized = result.strip().lower()
        if normalized in {"w", "win"}:
            return "win"
        if normalized in {"l", "loss"}:
            return "loss"
        if normalized.startswith("draw"):
            return "draw"
        if normalized in {"nc", "no contest"}:
            return "nc"
        if normalized == "next":
            return "upcoming"
        return "other"
