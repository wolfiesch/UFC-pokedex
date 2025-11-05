"""Add composite index for favorites listing queries.

Revision ID: 2f4c1b62abde
Revises: 79abdd457621
Create Date: 2025-11-05 02:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "2f4c1b62abde"
down_revision = "79abdd457621"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_favorite_collections_user_id_created_at",
        "favorite_collections",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_favorite_collections_user_id_created_at",
        table_name="favorite_collections",
    )
