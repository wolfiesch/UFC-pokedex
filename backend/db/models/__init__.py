from __future__ import annotations

import uuid
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
    LargeBinary,
    String,
    Table,
    Index,
    UniqueConstraint,
    text,
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

    # Image validation fields
    image_quality_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Overall image quality score (0-100)"
    )
    image_resolution_width: Mapped[int | None] = mapped_column(
        Integer, nullable=True, doc="Image width in pixels"
    )
    image_resolution_height: Mapped[int | None] = mapped_column(
        Integer, nullable=True, doc="Image height in pixels"
    )
    has_face_detected: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        index=True,
        doc="Whether facial detection found a human face",
    )
    face_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, doc="Number of faces detected in image"
    )
    image_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
        doc="Timestamp of last image validation",
    )
    image_validation_flags: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Validation flags: low_resolution, no_face_detected, multiple_faces, potential_duplicate",
    )
    face_encoding: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True, doc="128-dimensional face encoding for duplicate detection"
    )

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
    last_fight_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
        doc="Date of fighter's most recent fight (for sorting by recent activity)",
    )

    # Location data fields (from UFC.com and Sherdog)
    birthplace_city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="City extracted from birthplace (e.g., 'Dublin')",
    )
    birthplace_country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Country extracted from birthplace (e.g., 'Ireland'). Indexed for country filters.",
    )
    birthplace: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Full birthplace string from UFC.com (e.g., 'Dublin, Ireland')",
    )
    nationality: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Nationality from Sherdog (e.g., 'Irish'). May differ from birthplace_country.",
    )
    fighting_out_of: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Fighting location from UFC.com (e.g., 'Las Vegas, Nevada, USA')",
    )
    training_gym: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Training gym name from UFC.com (e.g., 'SBG Ireland')",
    )
    training_city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Training city derived from gym location lookup",
    )
    training_country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Training country derived from gym location lookup",
    )

    # UFC.com cross-reference and matching metadata
    ufc_com_slug: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        doc="UFC.com athlete slug (e.g., 'conor-mcgregor') for future updates",
    )
    ufc_com_scraped_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        doc="Timestamp of last UFC.com data fetch for refresh scheduling",
    )
    ufc_com_match_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        doc="Fuzzy match confidence score (0-100) for UFC.com fighter matching",
    )
    ufc_com_match_method: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        doc="Match method: 'auto_high', 'auto_medium', 'manual', or 'verified'",
    )
    needs_manual_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="Flag for ambiguous matches or conflicting data requiring human verification",
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


class FighterRanking(Base):
    """Fighter rankings from various sources (UFC, Fight Matrix, etc.)."""

    __tablename__ = "fighter_rankings"
    __table_args__ = (
        Index("ix_fighter_rankings_fighter_date", "fighter_id", "rank_date"),
        Index("ix_fighter_rankings_division_date_source", "division", "rank_date", "source"),
        Index("ix_fighter_rankings_fighter_source", "fighter_id", "source"),
        Index(
            "ix_fighter_rankings_fighter_source_rankdate",
            "fighter_id",
            "source",
            "rank_date",
        ),
        Index(
            "ix_fighter_rankings_fighter_source_rank_rankdate",
            "fighter_id",
            "source",
            "rank",
            "rank_date",
            postgresql_where=text("rank IS NOT NULL"),
        ),
        UniqueConstraint(
            "fighter_id",
            "division",
            "rank_date",
            "source",
            name="uq_fighter_rankings_natural_key",
        ),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    fighter_id: Mapped[str] = mapped_column(
        ForeignKey("fighters.id"),
        nullable=False,
        doc="Foreign key to fighters table",
    )
    division: Mapped[str] = mapped_column(
        String(50), nullable=False, doc="Weight class (e.g., 'Lightweight')"
    )
    rank: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Rank position: 0=Champion, 1-15=Ranked, null=Not Ranked (NR)",
    )
    previous_rank: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Previous rank for movement tracking (e.g., ↑2, ↓1)",
    )
    rank_date: Mapped[date] = mapped_column(
        Date, nullable=False, doc="Date of this ranking snapshot"
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Ranking source: 'ufc', 'fightmatrix', 'tapology'",
    )
    is_interim: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, doc="Whether this is an interim championship"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Timestamp when ranking was recorded",
    )

    # Relationship
    fighter: Mapped[Fighter] = relationship("Fighter")


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
    "FighterRanking",
    "FavoriteCollection",
    "FavoriteEntry",
    "fighter_stats",
]
