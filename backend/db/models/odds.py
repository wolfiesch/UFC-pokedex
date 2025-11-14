"""SQLAlchemy model definitions for fighter betting odds records."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base

QUALITY_CHOICES = ("excellent", "good", "usable", "poor", "no_data")


class FighterOdds(Base):
    """Represents aggregated time-series betting odds for a fighter's bout."""

    __tablename__ = "fighter_odds"
    __table_args__ = (
        UniqueConstraint(
            "fighter_id",
            "opponent_name",
            "event_name",
            name="uq_fighter_odds_fight",
        ),
        CheckConstraint(
            "data_quality_tier IN ('excellent','good','usable','poor','no_data') OR data_quality_tier IS NULL",
            name="ck_fighter_odds_quality_tier",
        ),
        Index("ix_fighter_odds_fighter_id", "fighter_id"),
        Index("ix_fighter_odds_event_date", "event_date"),
        Index("ix_fighter_odds_quality", "data_quality_tier"),
        Index("ix_fighter_odds_fighter_opponent", "fighter_id", "opponent_name"),
        # [*TO-DO*] - Add composite index for list_fighter_odds query performance:
        # Index('ix_fighter_odds_list_order', 'fighter_id',
        #       event_date.desc().nullslast(), scraped_at.desc())
        # This will optimize ORDER BY queries at scale (>100 fights per fighter)
    )

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        comment="Format: odds_{md5(fighter_id|opponent|event)}",
    )
    fighter_id: Mapped[str] = mapped_column(
        ForeignKey("fighters.id"),
        nullable=False,
        comment="Foreign key to fighters table (UFC Stats ID).",
    )
    opponent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    opening_odds: Mapped[str | None] = mapped_column(String(20), nullable=True)
    closing_range_start: Mapped[str | None] = mapped_column(String(20), nullable=True)
    closing_range_end: Mapped[str | None] = mapped_column(String(20), nullable=True)
    mean_odds_history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="Array of {timestamp_ms, timestamp, odds} time-series points.",
    )
    num_odds_points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of data points in time series.",
    )
    data_quality_tier: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Quality tier derived from num_odds_points.",
    )
    is_duplicate: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Flag retained for debugging historical duplicate detection.",
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        comment="Timestamp when the odds were scraped from BestFightOdds.",
    )
    bfo_fighter_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    fighter: Mapped["Fighter"] = relationship("Fighter")


__all__ = ["FighterOdds", "QUALITY_CHOICES"]
