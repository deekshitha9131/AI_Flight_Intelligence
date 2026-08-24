"""Add context_json column to chat_conversations for structured flight state.

Revision ID: 003_add_conversation_context
Revises: 002_add_user_columns
Create Date: 2026-08-19 06:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "003_add_conversation_context"
down_revision = "002_add_user_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_conversations",
        sa.Column("context_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_conversations", "context_json")
