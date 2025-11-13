"""add_fighting_out_of_field

Revision ID: 78d50ad4c659
Revises: fb11672df018
Create Date: 2025-11-11 12:39:37.157980

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "78d50ad4c659"
down_revision: Union[str, None] = "fb11672df018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add fighting_out_of column
    op.add_column("fighters", sa.Column("fighting_out_of", sa.String(255), nullable=True))

    # Add index for filtering by location
    op.create_index(
        op.f("ix_fighters_fighting_out_of"), "fighters", ["fighting_out_of"], unique=False
    )


def downgrade() -> None:
    # Drop index
    op.drop_index(op.f("ix_fighters_fighting_out_of"), table_name="fighters")

    # Drop column
    op.drop_column("fighters", "fighting_out_of")
