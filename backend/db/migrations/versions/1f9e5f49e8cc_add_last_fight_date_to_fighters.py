"""add_last_fight_date_to_fighters

Revision ID: 1f9e5f49e8cc
Revises: f912d517b732
Create Date: 2025-11-10 21:17:56.766348

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f9e5f49e8cc'
down_revision: Union[str, None] = 'f912d517b732'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add last_fight_date column to fighters table
    op.add_column('fighters', sa.Column('last_fight_date', sa.Date(), nullable=True))

    # Create index for sorting performance
    op.create_index(op.f('ix_fighters_last_fight_date'), 'fighters', ['last_fight_date'], unique=False)

    # Populate last_fight_date from existing fight data
    # This SQL finds the most recent fight date for each fighter
    op.execute("""
        UPDATE fighters
        SET last_fight_date = (
            SELECT MAX(event_date)
            FROM fights
            WHERE fights.fighter_id = fighters.id OR fights.opponent_id = fighters.id
        )
    """)


def downgrade() -> None:
    # Drop index and column
    op.drop_index(op.f('ix_fighters_last_fight_date'), table_name='fighters')
    op.drop_column('fighters', 'last_fight_date')
