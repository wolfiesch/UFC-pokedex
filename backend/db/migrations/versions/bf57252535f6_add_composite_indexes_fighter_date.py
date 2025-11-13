"""add_composite_indexes_fighter_date

Revision ID: bf57252535f6
Revises: fecf7c9009ab
Create Date: 2025-11-05 00:22:53.133415

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bf57252535f6"
down_revision: str | None = "fecf7c9009ab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add composite indexes for optimized fight history queries.

    These indexes dramatically improve performance when sorting fights by date
    for a specific fighter (common pattern in streak computation and fight history).
    """
    # Composite index for fighter_id + event_date
    # Optimizes queries like: SELECT * FROM fights WHERE fighter_id = ? ORDER BY event_date DESC
    op.create_index(
        "ix_fights_fighter_id_event_date", "fights", ["fighter_id", "event_date"], unique=False
    )

    # Composite index for opponent_id + event_date
    # Needed because we query fights from both fighter and opponent perspectives
    op.create_index(
        "ix_fights_opponent_id_event_date", "fights", ["opponent_id", "event_date"], unique=False
    )


def downgrade() -> None:
    """Remove composite indexes."""
    op.drop_index("ix_fights_fighter_id_event_date", table_name="fights")
    op.drop_index("ix_fights_opponent_id_event_date", table_name="fights")
