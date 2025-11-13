"""Initial schema

Revision ID: c82d463a5926
Revises:
Create Date: 2025-10-30 18:07:13.036254

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c82d463a5926"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create fighters table
    op.create_table(
        "fighters",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("nickname", sa.String(), nullable=True),
        sa.Column("division", sa.String(), nullable=True),
        sa.Column("height", sa.String(), nullable=True),
        sa.Column("weight", sa.String(), nullable=True),
        sa.Column("reach", sa.String(), nullable=True),
        sa.Column("leg_reach", sa.String(), nullable=True),
        sa.Column("stance", sa.String(), nullable=True),
        sa.Column("dob", sa.Date(), nullable=True),
        sa.Column("record", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create fights table
    op.create_table(
        "fights",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("fighter_id", sa.String(), nullable=False),
        sa.Column("opponent_id", sa.String(), nullable=True),
        sa.Column("opponent_name", sa.String(), nullable=False),
        sa.Column("event_name", sa.String(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("result", sa.String(), nullable=False),
        sa.Column("method", sa.String(), nullable=True),
        sa.Column("round", sa.Integer(), nullable=True),
        sa.Column("time", sa.String(), nullable=True),
        sa.Column("fight_card_url", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["fighter_id"],
            ["fighters.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create fighter_stats table
    op.create_table(
        "fighter_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fighter_id", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("metric", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["fighter_id"],
            ["fighters.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("fighter_stats")
    op.drop_table("fights")
    op.drop_table("fighters")
