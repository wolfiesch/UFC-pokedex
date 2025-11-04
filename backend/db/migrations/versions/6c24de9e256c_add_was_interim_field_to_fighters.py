"""add_was_interim_field_to_fighters

Revision ID: 6c24de9e256c
Revises: 685cededf16b
Create Date: 2025-11-04 15:07:43.782963

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c24de9e256c'
down_revision: Union[str, None] = '685cededf16b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add was_interim column to fighters table
    op.add_column(
        'fighters',
        sa.Column('was_interim', sa.Boolean(), nullable=False, server_default='false')
    )

    # Create index for performance
    op.create_index(
        'ix_fighters_was_interim',
        'fighters',
        ['was_interim'],
        unique=False
    )


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_fighters_was_interim', table_name='fighters')

    # Drop column
    op.drop_column('fighters', 'was_interim')
