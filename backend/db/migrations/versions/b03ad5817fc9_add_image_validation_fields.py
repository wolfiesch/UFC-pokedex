"""add_image_validation_fields

Revision ID: b03ad5817fc9
Revises: 1f9e5f49e8cc
Create Date: 2025-11-11 00:38:05.511962

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b03ad5817fc9"
down_revision: Union[str, None] = "1f9e5f49e8cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add image validation fields to fighters table
    op.add_column("fighters", sa.Column("image_quality_score", sa.Float(), nullable=True))
    op.add_column("fighters", sa.Column("image_resolution_width", sa.Integer(), nullable=True))
    op.add_column("fighters", sa.Column("image_resolution_height", sa.Integer(), nullable=True))
    op.add_column("fighters", sa.Column("has_face_detected", sa.Boolean(), nullable=True))
    op.add_column("fighters", sa.Column("face_count", sa.Integer(), nullable=True))
    op.add_column("fighters", sa.Column("image_validated_at", sa.DateTime(), nullable=True))
    op.add_column("fighters", sa.Column("image_validation_flags", sa.JSON(), nullable=True))
    op.add_column("fighters", sa.Column("face_encoding", sa.LargeBinary(), nullable=True))

    # Add index for quick lookup of fighters with validation issues
    op.create_index("ix_fighters_has_face_detected", "fighters", ["has_face_detected"])
    op.create_index("ix_fighters_image_validated_at", "fighters", ["image_validated_at"])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index("ix_fighters_image_validated_at", table_name="fighters")
    op.drop_index("ix_fighters_has_face_detected", table_name="fighters")

    # Drop columns
    op.drop_column("fighters", "face_encoding")
    op.drop_column("fighters", "image_validation_flags")
    op.drop_column("fighters", "image_validated_at")
    op.drop_column("fighters", "face_count")
    op.drop_column("fighters", "has_face_detected")
    op.drop_column("fighters", "image_resolution_height")
    op.drop_column("fighters", "image_resolution_width")
    op.drop_column("fighters", "image_quality_score")
