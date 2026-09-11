"""Add model_version to prediction table

Revision ID: e1fb3efa5490
Revises: 09e44e99b627
Create Date: 2026-08-30 11:56:46.816338

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1fb3efa5490'
down_revision: Union[str, None] = '09e44e99b627'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add model_version column to prediction table
    op.add_column('predictions', sa.Column('model_version', sa.String(length=20), nullable=False, server_default='v1.0.0'))


def downgrade() -> None:
    # Remove model_version column from prediction table
    op.drop_column('predictions', 'model_version')