"""add_events_table_and_link_to_fights

Revision ID: b34c3a5cd0e1
Revises: 01c24964ee70
Create Date: 2025-11-03 20:47:22.137103

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b34c3a5cd0e1"
down_revision: str | None = "01c24964ee70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create events table
    op.create_table(
        "events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("venue", sa.String(), nullable=True),
        sa.Column("broadcast", sa.String(), nullable=True),
        sa.Column("promotion", sa.String(), nullable=False, server_default="UFC"),
        sa.Column("ufcstats_url", sa.String(), nullable=False),
        sa.Column("tapology_url", sa.String(), nullable=True),
        sa.Column("sherdog_url", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes on events table
    op.create_index(op.f("ix_events_date"), "events", ["date"], unique=False)
    op.create_index(op.f("ix_events_status"), "events", ["status"], unique=False)

    # Add event_id column to fights table
    op.add_column("fights", sa.Column("event_id", sa.String(), nullable=True))

    # Create foreign key constraint and index
    op.create_foreign_key("fk_fights_event_id", "fights", "events", ["event_id"], ["id"])
    op.create_index(op.f("ix_fights_event_id"), "fights", ["event_id"], unique=False)


def downgrade() -> None:
    # Drop foreign key and index from fights table
    op.drop_index(op.f("ix_fights_event_id"), table_name="fights")
    op.drop_constraint("fk_fights_event_id", "fights", type_="foreignkey")

    # Drop event_id column from fights table
    op.drop_column("fights", "event_id")

    # Drop indexes from events table
    op.drop_index(op.f("ix_events_status"), table_name="events")
    op.drop_index(op.f("ix_events_date"), table_name="events")

    # Drop events table
    op.drop_table("events")
