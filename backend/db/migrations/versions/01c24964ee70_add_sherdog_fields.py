"""add_sherdog_fields

Revision ID: 01c24964ee70
Revises: c82d463a5926
Create Date: 2025-11-01 20:59:11.696165

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "01c24964ee70"
down_revision: str | None = "c82d463a5926"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("fighters", sa.Column("sherdog_id", sa.Integer(), nullable=True))
    op.add_column("fighters", sa.Column("image_url", sa.String(), nullable=True))
    op.add_column("fighters", sa.Column("image_scraped_at", sa.DateTime(), nullable=True))
    op.create_index(op.f("ix_fighters_sherdog_id"), "fighters", ["sherdog_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_fighters_sherdog_id"), table_name="fighters")
    op.drop_column("fighters", "image_scraped_at")
    op.drop_column("fighters", "image_url")
    op.drop_column("fighters", "sherdog_id")
