"""add favorites tables

Revision ID: d3a04e3f94bb
Revises: 6c24de9e256c
Create Date: 2025-11-04 23:30:00.000000
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "d3a04e3f94bb"
down_revision: str | None = "6c24de9e256c"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "favorite_collections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=True),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
        sa.Column(
            "metadata_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.UniqueConstraint(
            "user_id",
            "slug",
            name="uq_favorite_collections_user_slug",
        ),
    )

    op.create_index(
        "ix_favorite_collections_user_id",
        "favorite_collections",
        ["user_id"],
    )
    op.create_index(
        "ix_favorite_collections_slug",
        "favorite_collections",
        ["slug"],
    )

    op.create_table(
        "favorite_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("fighter_id", sa.String(), nullable=False),
        sa.Column(
            "position",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("notes", sa.String(length=1024), nullable=True),
        sa.Column(
            "tags",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
        sa.Column(
            "metadata_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["favorite_collections.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["fighter_id"],
            ["fighters.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "collection_id",
            "fighter_id",
            name="uq_favorite_entries_collection_fighter",
        ),
    )

    op.create_index(
        "ix_favorite_entries_collection_id",
        "favorite_entries",
        ["collection_id"],
    )
    op.create_index(
        "ix_favorite_entries_fighter_id",
        "favorite_entries",
        ["fighter_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_favorite_entries_fighter_id", table_name="favorite_entries")
    op.drop_index("ix_favorite_entries_collection_id", table_name="favorite_entries")
    op.drop_table("favorite_entries")

    op.drop_index("ix_favorite_collections_slug", table_name="favorite_collections")
    op.drop_index("ix_favorite_collections_user_id", table_name="favorite_collections")
    op.drop_table("favorite_collections")
