"""add fighter odds table

Revision ID: c88abbcd9d1f
Revises: 805e2f7ba7ce
Create Date: 2025-02-15 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c88abbcd9d1f"
down_revision: Union[str, None] = "805e2f7ba7ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fighter_odds",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("fighter_id", sa.String(), nullable=False),
        sa.Column("opponent_name", sa.String(length=255), nullable=False),
        sa.Column("event_name", sa.String(length=255), nullable=False),
        sa.Column("event_url", sa.String(length=512), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("opening_odds", sa.String(length=20), nullable=True),
        sa.Column("closing_range_start", sa.String(length=20), nullable=True),
        sa.Column("closing_range_end", sa.String(length=20), nullable=True),
        sa.Column(
            "mean_odds_history",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("num_odds_points", sa.Integer(), nullable=False),
        sa.Column("data_quality_tier", sa.String(length=20), nullable=True),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False),
        sa.Column("scraped_at", sa.DateTime(), nullable=False),
        sa.Column("bfo_fighter_url", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["fighter_id"], ["fighters.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "fighter_id",
            "opponent_name",
            "event_name",
            name="uq_fighter_odds_fight",
        ),
        sa.CheckConstraint(
            "data_quality_tier IN ('excellent','good','usable','poor','no_data') OR data_quality_tier IS NULL",
            name="ck_fighter_odds_quality_tier",
        ),
    )
    op.create_index(
        "ix_fighter_odds_fighter_id", "fighter_odds", ["fighter_id"], unique=False
    )
    op.create_index(
        "ix_fighter_odds_event_date", "fighter_odds", ["event_date"], unique=False
    )
    op.create_index(
        "ix_fighter_odds_quality", "fighter_odds", ["data_quality_tier"], unique=False
    )
    op.create_index(
        "ix_fighter_odds_fighter_opponent",
        "fighter_odds",
        ["fighter_id", "opponent_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_fighter_odds_fighter_opponent", table_name="fighter_odds"
    )
    op.drop_index("ix_fighter_odds_quality", table_name="fighter_odds")
    op.drop_index("ix_fighter_odds_event_date", table_name="fighter_odds")
    op.drop_index("ix_fighter_odds_fighter_id", table_name="fighter_odds")
    op.drop_table("fighter_odds")
