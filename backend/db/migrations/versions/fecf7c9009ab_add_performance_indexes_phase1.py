"""add_performance_indexes_phase1

Revision ID: fecf7c9009ab
Revises: 8a8176360005
Create Date: 2025-11-05 00:02:29.482444

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'fecf7c9009ab'
down_revision: Union[str, None] = '8a8176360005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add index for fighters.division (heavy filtering use)
    op.create_index('ix_fighters_division', 'fighters', ['division'], unique=False)

    # Add index for fighters.stance (search filter use)
    op.create_index('ix_fighters_stance', 'fighters', ['stance'], unique=False)

    # Add index for fights.event_date (sorting/date queries)
    op.create_index('ix_fights_event_date', 'fights', ['event_date'], unique=False)

    # Add index for fighter_stats.fighter_id (stats lookups)
    op.create_index(
        'ix_fighter_stats_fighter_id', 'fighter_stats', ['fighter_id'], unique=False
    )


def downgrade() -> None:
    # Drop indexes in reverse order
    op.drop_index('ix_fighter_stats_fighter_id', table_name='fighter_stats')
    op.drop_index('ix_fights_event_date', table_name='fights')
    op.drop_index('ix_fighters_stance', table_name='fighters')
    op.drop_index('ix_fighters_division', table_name='fighters')
