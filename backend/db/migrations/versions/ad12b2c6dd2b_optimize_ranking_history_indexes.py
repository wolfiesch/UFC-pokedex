"""optimize_ranking_history_indexes

Revision ID: ad12b2c6dd2b
Revises: fecf7c9009ab
Create Date: 2025-11-10 06:05:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ad12b2c6dd2b'
down_revision: str | None = 'fecf7c9009ab'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Supports fighter history queries (fighter_id + source ordered by date)
    op.create_index(
        'ix_fighter_rankings_fighter_source_rankdate',
        'fighter_rankings',
        ['fighter_id', 'source', 'rank_date'],
        unique=False,
    )

    # Supports peak-rank lookups (ignores NR rows, preserves order requirements)
    op.create_index(
        'ix_fighter_rankings_fighter_source_rank_rankdate',
        'fighter_rankings',
        ['fighter_id', 'source', 'rank', 'rank_date'],
        unique=False,
        postgresql_where=sa.text('rank IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index(
        'ix_fighter_rankings_fighter_source_rank_rankdate',
        table_name='fighter_rankings',
    )
    op.drop_index(
        'ix_fighter_rankings_fighter_source_rankdate',
        table_name='fighter_rankings',
    )
