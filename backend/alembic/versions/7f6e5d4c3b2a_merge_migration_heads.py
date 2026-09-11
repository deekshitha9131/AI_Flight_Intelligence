"""Merge the phase 14 and favourites migration heads.

Revision ID: 7f6e5d4c3b2a
Revises: c806b2af4206, 5c2c1d6f4a91
"""
from typing import Sequence, Union


revision: str = '7f6e5d4c3b2a'
down_revision: Union[str, Sequence[str], None] = ('c806b2af4206', '5c2c1d6f4a91')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass