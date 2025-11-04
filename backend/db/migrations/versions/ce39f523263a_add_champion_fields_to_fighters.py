"""add_champion_fields_to_fighters

Revision ID: ce39f523263a
Revises: 6b7a839d5f5c
Create Date: 2025-11-04 12:32:44.088286

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce39f523263a'
down_revision: Union[str, None] = '6b7a839d5f5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add champion status fields to fighters table."""
    # Add champion status columns
    op.add_column(
        'fighters',
        sa.Column('is_current_champion', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )
    op.add_column(
        'fighters',
        sa.Column('is_former_champion', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )
    op.add_column(
        'fighters',
        sa.Column('championship_history', sa.JSON(), nullable=True)
    )

    # Create indexes for champion status fields
    op.create_index(op.f('ix_fighters_is_current_champion'), 'fighters', ['is_current_champion'], unique=False)
    op.create_index(op.f('ix_fighters_is_former_champion'), 'fighters', ['is_former_champion'], unique=False)


def downgrade() -> None:
    """Remove champion status fields from fighters table."""
    # Drop indexes
    op.drop_index(op.f('ix_fighters_is_former_champion'), table_name='fighters')
    op.drop_index(op.f('ix_fighters_is_current_champion'), table_name='fighters')

    # Drop columns
    op.drop_column('fighters', 'championship_history')
    op.drop_column('fighters', 'is_former_champion')
    op.drop_column('fighters', 'is_current_champion')
