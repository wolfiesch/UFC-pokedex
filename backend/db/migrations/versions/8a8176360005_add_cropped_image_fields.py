"""add_cropped_image_fields

Revision ID: 8a8176360005
Revises: d3a04e3f94bb
Create Date: 2025-11-04 21:31:38.829479

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8a8176360005'
down_revision: str | None = 'd3a04e3f94bb'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add cropped image fields to fighters table
    op.add_column('fighters', sa.Column('cropped_image_url', sa.String(), nullable=True))
    op.add_column('fighters', sa.Column('face_detection_confidence', sa.Float(), nullable=True))
    op.add_column('fighters', sa.Column('crop_processed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove cropped image fields from fighters table
    op.drop_column('fighters', 'crop_processed_at')
    op.drop_column('fighters', 'face_detection_confidence')
    op.drop_column('fighters', 'cropped_image_url')
