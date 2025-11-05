"""add_name_id_index_fighters

Revision ID: 6e7f2cce1b8b
Revises: 2f4c1b62abde
Create Date: 2025-11-05 02:45:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6e7f2cce1b8b"
down_revision: str | None = "2f4c1b62abde"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add composite index to accelerate roster paging queries."""
    op.create_index(
        "ix_fighters_name_id",
        "fighters",
        ["name", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop composite index for fighters roster paging."""
    op.drop_index("ix_fighters_name_id", table_name="fighters")
