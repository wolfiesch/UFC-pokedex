"""add_fighter_rankings_table

Revision ID: f143b7233ba8
Revises: 1098d00ea248
Create Date: 2025-11-09 19:57:36.645008

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f143b7233ba8"
down_revision: Union[str, None] = "1098d00ea248"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create fighter_rankings table
    op.create_table(
        "fighter_rankings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("fighter_id", sa.String(), nullable=False),
        sa.Column("division", sa.String(length=50), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("previous_rank", sa.Integer(), nullable=True),
        sa.Column("rank_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("is_interim", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(
            ["fighter_id"],
            ["fighters.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "fighter_id", "division", "rank_date", "source", name="uq_fighter_rankings_natural_key"
        ),
    )

    # Create indexes
    op.create_index(
        "ix_fighter_rankings_fighter_date",
        "fighter_rankings",
        ["fighter_id", "rank_date"],
        unique=False,
    )
    op.create_index(
        "ix_fighter_rankings_division_date_source",
        "fighter_rankings",
        ["division", "rank_date", "source"],
        unique=False,
    )
    op.create_index(
        "ix_fighter_rankings_fighter_source",
        "fighter_rankings",
        ["fighter_id", "source"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_fighter_rankings_fighter_source", table_name="fighter_rankings")
    op.drop_index("ix_fighter_rankings_division_date_source", table_name="fighter_rankings")
    op.drop_index("ix_fighter_rankings_fighter_date", table_name="fighter_rankings")

    # Drop table
    op.drop_table("fighter_rankings")
