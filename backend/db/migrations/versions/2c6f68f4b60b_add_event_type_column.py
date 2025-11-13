"""add event_type column and backfill existing events."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session

from backend.utils.event_utils import detect_event_type

# revision identifiers, used by Alembic.
revision: str = "2c6f68f4b60b"
down_revision: str = "805e2f7ba7ce"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Add the ``event_type`` column and populate existing rows."""

    op.add_column(
        "events",
        sa.Column(
            "event_type",
            sa.String(length=32),
            nullable=False,
            server_default="other",
        ),
    )
    op.create_index("ix_events_event_type", "events", ["event_type"], unique=False)

    events_table = sa.table(
        "events",
        sa.column("id", sa.String()),
        sa.column("name", sa.String()),
        sa.column("event_type", sa.String()),
    )

    bind = op.get_bind()
    session = Session(bind=bind)

    try:
        with session.begin():
            rows = session.execute(
                sa.select(events_table.c.id, events_table.c.name)
            ).all()
            for event_id, event_name in rows:
                normalized_event_name: str = event_name or ""
                detected_type: str = detect_event_type(normalized_event_name).value
                session.execute(
                    events_table.update()
                    .where(events_table.c.id == event_id)
                    .values(event_type=detected_type)
                )
    finally:
        session.close()


def downgrade() -> None:
    """Remove the ``event_type`` column and companion index."""

    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_column("events", "event_type")
