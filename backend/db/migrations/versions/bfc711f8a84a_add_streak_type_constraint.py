"""add_streak_type_constraint

Revision ID: bfc711f8a84a
Revises: b502e054dc5b
Create Date: 2025-11-05 18:50:34.023937

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bfc711f8a84a'
down_revision: Union[str, None] = 'b502e054dc5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE fighters
        ADD CONSTRAINT check_streak_type
        CHECK (current_streak_type IN ('win', 'loss', 'draw', 'none') OR current_streak_type IS NULL)
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE fighters DROP CONSTRAINT check_streak_type")
