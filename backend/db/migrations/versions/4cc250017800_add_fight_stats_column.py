"""add_fight_stats_column

Revision ID: 4cc250017800
Revises: b34c3a5cd0e1
Create Date: 2025-02-16 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4cc250017800"
down_revision: Union[str, None] = "b34c3a5cd0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a JSON stats payload to fights for per-bout metrics."""

    op.add_column(
        "fights",
        sa.Column(
            "stats",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.execute(sa.text("UPDATE fights SET stats = '{}' WHERE stats IS NULL"))
    op.alter_column("fights", "stats", server_default=None)


def downgrade() -> None:
    """Remove the per-bout stats payload column."""

    op.drop_column("fights", "stats")
