"""add_composite_index_opponent_event_date

Revision ID: 50d600794d2b
Revises: bfc711f8a84a
Create Date: 2025-11-06 02:37:01.850980

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "50d600794d2b"
down_revision: Union[str, None] = "bfc711f8a84a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create composite index on (opponent_id, event_date DESC NULLS LAST)
    # This speeds up queries that filter by opponent_id and sort by event_date
    op.create_index(
        "ix_fights_opponent_event_date",
        "fights",
        ["opponent_id", sa.text("event_date DESC NULLS LAST")],
        unique=False,
    )


def downgrade() -> None:
    # Remove the composite index
    op.drop_index("ix_fights_opponent_event_date", table_name="fights")
