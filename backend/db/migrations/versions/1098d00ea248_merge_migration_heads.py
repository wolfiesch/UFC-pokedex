"""merge_migration_heads

Revision ID: 1098d00ea248
Revises: 50d600794d2b, a6bde4fb7b5b
Create Date: 2025-11-09 19:57:28.048580

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1098d00ea248'
down_revision: Union[str, None] = ('50d600794d2b', 'a6bde4fb7b5b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
