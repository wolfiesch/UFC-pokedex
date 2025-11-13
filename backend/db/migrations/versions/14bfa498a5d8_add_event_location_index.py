"""add_event_location_index

Revision ID: 14bfa498a5d8
Revises: 78d50ad4c659
Create Date: 2025-11-11 12:52:34.886725

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "14bfa498a5d8"
down_revision: Union[str, None] = "78d50ad4c659"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f("ix_events_location"), "events", ["location"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_events_location"), table_name="events")
