"""make_event_ufcstats_url_nullable

Revision ID: a6bde4fb7b5b
Revises: b34c3a5cd0e1
Create Date: 2025-11-08 05:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a6bde4fb7b5b"
down_revision: str | None = "b34c3a5cd0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "events",
        "ufcstats_url",
        existing_type=sa.String(),
        existing_nullable=False,
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "events",
        "ufcstats_url",
        existing_type=sa.String(),
        existing_nullable=True,
        nullable=False,
    )
