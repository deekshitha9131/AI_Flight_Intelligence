"""Add missing user columns for registration and profile fields.

Revision ID: 002_add_user_columns
Revises: 001_ai_tables
Create Date: 2026-08-05 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "002_add_user_columns"
down_revision = "001_ai_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("preferred_airport", sa.String(length=3), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("preferred_cabin", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("currency_preference", sa.String(length=3), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("notification_settings", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "notification_settings")
    op.drop_column("users", "currency_preference")
    op.drop_column("users", "preferred_cabin")
    op.drop_column("users", "preferred_airport")
