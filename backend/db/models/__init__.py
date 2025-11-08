from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Index,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    validates,
)


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    location: Mapped[str | None]
    status: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )  # 'upcoming' or 'completed'

    # Enhanced metadata (from Tapology or other sources)
    venue: Mapped[str | None]
    broadcast: Mapped[str | None]
    promotion: Mapped[str] = mapped_column(String, nullable=False, default="UFC")

    # Cross-reference URLs
    ufcstats_url: Mapped[str | None] = mapped_column(String, nullable=True)
    tapology_url: Mapped[str | None]
    sherdog_url: Mapped[str | None]

    # Relationships
    fights: Mapped[list[Fight]] = relationship("Fight", back_populates="event")


class Fighter(Base):
    __tablename__ = "fighters"
    __table_args__ = (Index("ix_fighters_name_id", "name", "id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    nickname: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
        doc=(
            "Index ensures quick nickname lookups for fighter search "
            "and autocomplete queries."
        ),
    )
    division: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        doc="Indexed for division filtering queries",
    )
    height: Mapped[str | None]
    weight: Mapped[str | None]
    reach: Mapped[str | None]
    leg_reach: Mapped[str | None]
    stance: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
        doc="Indexed for stance filtering queries",
    )
    dob: Mapped[date | None]
    record: Mapped[str | None]
    sherdog_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    image_scraped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cropped_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    face_detection_confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    crop_processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Champion status fields
    is_current_champion: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    is_former_champion: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    was_interim: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    championship_history: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )

    # Pre-computed streak columns for performance (Phase 2 optimization)
    current_streak_type: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        index=True,
        doc="Current streak type: 'win', 'loss', 'draw', or None",
    )
    current_streak_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        index=True,
        doc="Count of current streak (computed from recent fight history)",
    )

    fights: Mapped[list[Fight]] = relationship("Fight", back_populates="fighter")

    @validates("current_streak_type")
    def validate_streak_type(self, key: str, value: str | None) -> str | None:
        """Validate that streak type is one of the allowed values."""
        if value is not None and value not in ("win", "loss", "draw", "none"):
            raise ValueError(
                f"Invalid streak type '{value}'. Must be one of: win, loss, draw, none"
            )
        return value


class Fight(Base):
    __tablename__ = "fights"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    fighter_id: Mapped[str] = mapped_column(
        ForeignKey("fighters.id"),
        nullable=False,
        index=True,
        doc="Index optimizes fighter fight history retrieval and aggregation queries.",
    )
    event_id: Mapped[str | None] = mapped_column(
        ForeignKey("events.id"), nullable=True, index=True
    )
    opponent_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
        doc=(
            "Optional index accelerates opponent-based lookups during event "
            "and rivalry analysis pipelines."
        ),
    )
    opponent_name: Mapped[str] = mapped_column(String, nullable=False)
    event_name: Mapped[str] = mapped_column(
        String, nullable=False
    )  # Keep for backward compatibility
    event_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
        doc="Indexed for date sorting/filtering queries",
    )
    result: Mapped[str] = mapped_column(String, nullable=False)
    method: Mapped[str | None]
    round: Mapped[int | None]
    time: Mapped[str | None]
    fight_card_url: Mapped[str | None]
    stats: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    weight_class: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        doc="Recorded weight class label for the bout (e.g., Lightweight).",
    )

    fighter: Mapped[Fighter] = relationship("Fighter", back_populates="fights")
    event: Mapped[Event | None] = relationship("Event", back_populates="fights")


fighter_stats = Table(
    "fighter_stats",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("fighter_id", ForeignKey("fighters.id"), nullable=False, index=True),
    Column("category", String, nullable=False),
    Column("metric", String, nullable=False),
    Column("value", String, nullable=False),
)

# Imported late to avoid circular dependency with favorites module.
from .favorites import FavoriteCollection, FavoriteEntry  # noqa: E402

__all__ = [
    "Base",
    "Event",
    "Fight",
    "Fighter",
    "FavoriteCollection",
    "FavoriteEntry",
    "fighter_stats",
]
