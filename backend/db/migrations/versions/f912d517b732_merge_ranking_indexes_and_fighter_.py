"""merge ranking indexes and fighter ranking table

Revision ID: f912d517b732
Revises: ad12b2c6dd2b, f143b7233ba8
Create Date: 2025-11-10 05:35:08.514923

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f912d517b732'
down_revision: Union[str, None] = ('ad12b2c6dd2b', 'f143b7233ba8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
