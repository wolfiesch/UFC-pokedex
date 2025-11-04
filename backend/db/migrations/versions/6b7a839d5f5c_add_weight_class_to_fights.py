"""add_weight_class_to_fights

Revision ID: 6b7a839d5f5c
Revises: 4cc250017800
Create Date: 2025-11-04 09:58:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6b7a839d5f5c"
down_revision: Union[str, None] = "4cc250017800"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the nullable ``weight_class`` column to the ``fights`` table."""

    op.add_column(
        "fights",
        sa.Column("weight_class", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Remove the ``weight_class`` column from the ``fights`` table."""

    op.drop_column("fights", "weight_class")
