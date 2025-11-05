"""add_fighter_streak_columns

Revision ID: b502e054dc5b
Revises: 6e7f2cce1b8b
Create Date: 2025-11-05 03:20:19.422763

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b502e054dc5b'
down_revision: str | None = '6e7f2cce1b8b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add pre-computed streak columns to fighters table for performance."""
    # Add streak columns
    op.add_column(
        'fighters',
        sa.Column('current_streak_type', sa.String(10), nullable=True),
    )
    op.add_column(
        'fighters',
        sa.Column(
            'current_streak_count',
            sa.Integer(),
            nullable=False,
            server_default='0',
        ),
    )

    # Create indexes for streak filtering performance
    op.create_index(
        op.f('ix_fighters_current_streak_type'),
        'fighters',
        ['current_streak_type'],
        unique=False,
    )
    op.create_index(
        op.f('ix_fighters_current_streak_count'),
        'fighters',
        ['current_streak_count'],
        unique=False,
    )
    # Composite index for streak queries (WHERE type = X AND count >= Y)
    op.create_index(
        'ix_fighters_streak_composite',
        'fighters',
        ['current_streak_type', 'current_streak_count'],
        unique=False,
    )


def downgrade() -> None:
    """Remove streak columns from fighters table."""
    # Drop indexes
    op.drop_index('ix_fighters_streak_composite', table_name='fighters')
    op.drop_index(
        op.f('ix_fighters_current_streak_count'), table_name='fighters'
    )
    op.drop_index(op.f('ix_fighters_current_streak_type'), table_name='fighters')

    # Drop columns
    op.drop_column('fighters', 'current_streak_count')
    op.drop_column('fighters', 'current_streak_type')
