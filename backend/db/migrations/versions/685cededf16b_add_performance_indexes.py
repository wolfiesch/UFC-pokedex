"""add_performance_indexes

Revision ID: 685cededf16b
Revises: ce39f523263a
Create Date: 2025-11-04 22:31:03.882697

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "685cededf16b"
down_revision: Union[str, None] = "ce39f523263a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add high-impact indexes that were previously missing."""

    # Fighter indexes power roster search and autocompletion workflows.
    op.create_index(
        "ix_fighters_name",
        "fighters",
        ["name"],
        unique=False,
    )
    op.create_index(
        "ix_fighters_nickname",
        "fighters",
        ["nickname"],
        unique=False,
    )

    # Fight indexes collapse per-bout lookups into indexed scans.
    op.create_index(
        "ix_fights_fighter_id",
        "fights",
        ["fighter_id"],
        unique=False,
    )
    op.create_index(
        "ix_fights_opponent_id",
        "fights",
        ["opponent_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove indexes added in :func:`upgrade`."""

    op.drop_index("ix_fights_opponent_id", table_name="fights")
    op.drop_index("ix_fights_fighter_id", table_name="fights")
    op.drop_index("ix_fighters_nickname", table_name="fighters")
    op.drop_index("ix_fighters_name", table_name="fighters")
