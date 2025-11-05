"""SQLAlchemy ORM models for user curated favorite collections.

These tables allow end users to assemble custom fighter collections and track
per-collection activity such as drag-and-drop ordering, personal notes, and
historical stats snapshots.  The ORM definitions mirror the API contract used
by the favorites dashboard and are extensively type annotated to keep the
codebase approachable.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base, Fighter


def utcnow():
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class FavoriteCollection(Base):
    """A curated list of fighters maintained by a single user."""

    __tablename__ = "favorite_collections"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "slug",
            name="uq_favorite_collections_user_slug",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
        doc=(
            "Opaque identifier for the owning user.  The backend treats this as"
            " a string so that API gateways can forward email addresses,"
            " UUIDs, or OAuth subject identifiers without additional schema"
            " churn."
        ),
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc=(
            "Optional slug generated from the title.  Slugs become stable"
            " anchors for bookmarkable URLs once collection sharing ships."
        ),
    )
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
        doc=(
            "Flexible JSON column reserved for lightweight feature flags such"
            " as default sorting preferences or pinned filters."
        ),
    )

    entries: Mapped[list["FavoriteEntry"]] = relationship(
        "FavoriteEntry",
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="FavoriteEntry.position",
    )


class FavoriteEntry(Base):
    """Association row that links a fighter to a specific collection."""

    __tablename__ = "favorite_entries"
    __table_args__ = (
        UniqueConstraint(
            "collection_id",
            "fighter_id",
            name="uq_favorite_entries_collection_fighter",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("favorite_collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fighter_id: Mapped[str] = mapped_column(
        ForeignKey("fighters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc=(
            "Zero-based ordering index used by the drag-and-drop UI.  The"
            " service keeps the sequence dense so that consumers can render"
            " fighters without client-side gaps."
        ),
    )
    notes: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
        doc="Arbitrary keywords supplied by the user to group fighters.",
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
        doc=(
            "Semi-structured details such as scouting grades or external"
            " profile links."
        ),
    )

    collection: Mapped[FavoriteCollection] = relationship(
        "FavoriteCollection", back_populates="entries"
    )
    fighter: Mapped[Fighter] = relationship("Fighter")
