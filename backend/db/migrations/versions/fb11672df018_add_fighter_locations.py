"""add_fighter_locations

Add geographical location fields to fighters table for birthplace,
nationality, training location, and UFC.com cross-reference data.

Revision ID: fb11672df018
Revises: b03ad5817fc9
Create Date: 2025-11-11 03:16:27.016090

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb11672df018'
down_revision: Union[str, None] = 'b03ad5817fc9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add geographical columns
    op.add_column('fighters', sa.Column('birthplace_city', sa.String(100), nullable=True))
    op.add_column('fighters', sa.Column('birthplace_country', sa.String(100), nullable=True))
    op.add_column('fighters', sa.Column('birthplace', sa.String(255), nullable=True))
    op.add_column('fighters', sa.Column('nationality', sa.String(100), nullable=True))
    op.add_column('fighters', sa.Column('training_gym', sa.String(255), nullable=True))
    op.add_column('fighters', sa.Column('training_city', sa.String(100), nullable=True))
    op.add_column('fighters', sa.Column('training_country', sa.String(100), nullable=True))

    # Add UFC.com cross-reference columns
    op.add_column('fighters', sa.Column('ufc_com_slug', sa.String(255), nullable=True))
    op.add_column('fighters', sa.Column('ufc_com_scraped_at', sa.DateTime(), nullable=True))

    # Add matching metadata columns
    op.add_column('fighters', sa.Column('ufc_com_match_confidence', sa.Float(), nullable=True))
    op.add_column('fighters', sa.Column('ufc_com_match_method', sa.String(20), nullable=True))
    op.add_column('fighters', sa.Column('needs_manual_review', sa.Boolean(),
                                       nullable=False, server_default='false'))

    # Add indexes for common queries
    op.create_index('ix_fighters_birthplace_country', 'fighters', ['birthplace_country'])
    op.create_index('ix_fighters_nationality', 'fighters', ['nationality'])
    op.create_index('ix_fighters_training_city', 'fighters', ['training_city'])
    op.create_index('ix_fighters_training_country', 'fighters', ['training_country'])
    op.create_index('ix_fighters_ufc_com_slug', 'fighters', ['ufc_com_slug'], unique=True)
    op.create_index('ix_fighters_needs_manual_review', 'fighters', ['needs_manual_review'])

    # Composite indexes for common filter combinations
    op.create_index('ix_fighters_birthplace_country_division', 'fighters',
                   ['birthplace_country', 'division'])
    op.create_index('ix_fighters_training_country_division', 'fighters',
                   ['training_country', 'division'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_fighters_training_country_division', 'fighters')
    op.drop_index('ix_fighters_birthplace_country_division', 'fighters')
    op.drop_index('ix_fighters_needs_manual_review', 'fighters')
    op.drop_index('ix_fighters_ufc_com_slug', 'fighters')
    op.drop_index('ix_fighters_training_country', 'fighters')
    op.drop_index('ix_fighters_training_city', 'fighters')
    op.drop_index('ix_fighters_nationality', 'fighters')
    op.drop_index('ix_fighters_birthplace_country', 'fighters')

    # Drop columns
    op.drop_column('fighters', 'needs_manual_review')
    op.drop_column('fighters', 'ufc_com_match_method')
    op.drop_column('fighters', 'ufc_com_match_confidence')
    op.drop_column('fighters', 'ufc_com_scraped_at')
    op.drop_column('fighters', 'ufc_com_slug')
    op.drop_column('fighters', 'training_country')
    op.drop_column('fighters', 'training_city')
    op.drop_column('fighters', 'training_gym')
    op.drop_column('fighters', 'nationality')
    op.drop_column('fighters', 'birthplace')
    op.drop_column('fighters', 'birthplace_country')
    op.drop_column('fighters', 'birthplace_city')
