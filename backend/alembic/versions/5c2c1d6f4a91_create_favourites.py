"""Create user flight favourites.

Revision ID: 5c2c1d6f4a91
Revises: e99b7797d4b3
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '5c2c1d6f4a91'
down_revision: Union[str, None] = 'e99b7797d4b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'favourites',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('flight_id', sa.String(length=100), nullable=False),
        sa.Column('airline', sa.String(length=255), nullable=False),
        sa.Column('flight_number', sa.String(length=100), nullable=False),
        sa.Column('origin', sa.String(length=3), nullable=False),
        sa.Column('destination', sa.String(length=3), nullable=False),
        sa.Column('departure_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('arrival_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=False),
        sa.Column('stops', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'flight_id', name='uq_favourites_user_flight'),
    )
    op.create_index('ix_favourites_user_id', 'favourites', ['user_id'])

def downgrade() -> None:
    op.drop_index('ix_favourites_user_id', table_name='favourites')
    op.drop_table('favourites')