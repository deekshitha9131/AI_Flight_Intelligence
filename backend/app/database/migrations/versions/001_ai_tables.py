"""Add AI tables: prediction_history, recommendation_logs, chat_conversations,
chat_messages, user_preference_profiles.

Revision ID: 001_ai_tables
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "001_ai_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # prediction_history                                                   #
    # ------------------------------------------------------------------ #
    op.create_table(
        "prediction_history",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("origin", sa.String(3), nullable=False),
        sa.Column("destination", sa.String(3), nullable=False),
        sa.Column("departure_date", sa.String(10), nullable=False),
        sa.Column("return_date", sa.String(10), nullable=True),
        sa.Column("airline", sa.String(10), nullable=True),
        sa.Column(
            "cabin_class", sa.String(20), nullable=False, server_default="ECONOMY"
        ),
        sa.Column("adults", sa.Integer, nullable=False, server_default="1"),
        sa.Column("children", sa.Integer, nullable=False, server_default="0"),
        sa.Column("infants", sa.Integer, nullable=False, server_default="0"),
        sa.Column("stops", sa.Integer, nullable=True),
        sa.Column("trip_type", sa.String(10), nullable=False, server_default="ONE_WAY"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("predicted_price", sa.Float, nullable=False),
        sa.Column("price_range_low", sa.Float, nullable=False),
        sa.Column("price_range_high", sa.Float, nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("estimated_savings", sa.Float, nullable=True),
        sa.Column("suggested_booking_window", sa.String(100), nullable=True),
        sa.Column(
            "model_version", sa.String(50), nullable=False, server_default="1.0.0"
        ),
        sa.Column("processing_time_ms", sa.Float, nullable=True),
        sa.Column("predicted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prediction_history_user_id", "prediction_history", ["user_id"])
    op.create_index(
        "ix_prediction_history_predicted_at", "prediction_history", ["predicted_at"]
    )

    # ------------------------------------------------------------------ #
    # recommendation_logs                                                  #
    # ------------------------------------------------------------------ #
    op.create_table(
        "recommendation_logs",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("recommendation_type", sa.String(30), nullable=False),
        sa.Column("payload", sa.Text, nullable=False, server_default="[]"),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_recommendation_logs_user_id", "recommendation_logs", ["user_id"]
    )
    op.create_index(
        "ix_recommendation_logs_type", "recommendation_logs", ["recommendation_type"]
    )
    op.create_index(
        "ix_recommendation_logs_created_at", "recommendation_logs", ["created_at"]
    )

    # ------------------------------------------------------------------ #
    # chat_conversations                                                   #
    # ------------------------------------------------------------------ #
    op.create_table(
        "chat_conversations",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "title", sa.String(200), nullable=False, server_default="New Conversation"
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chat_conversations_user_id", "chat_conversations", ["user_id"])
    op.create_index(
        "ix_chat_conversations_created_at", "chat_conversations", ["created_at"]
    )

    # ------------------------------------------------------------------ #
    # chat_messages                                                        #
    # ------------------------------------------------------------------ #
    op.create_table(
        "chat_messages",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("tokens_used", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"]
    )
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])

    # ------------------------------------------------------------------ #
    # user_preference_profiles                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "user_preference_profiles",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("preferred_airlines", sa.Text, nullable=False, server_default="[]"),
        sa.Column(
            "favorite_destinations", sa.Text, nullable=False, server_default="[]"
        ),
        sa.Column("frequent_origins", sa.Text, nullable=False, server_default="[]"),
        sa.Column("avg_budget", sa.Float, nullable=True),
        sa.Column("min_budget", sa.Float, nullable=True),
        sa.Column("max_budget", sa.Float, nullable=True),
        sa.Column(
            "preferred_cabin", sa.String(20), nullable=False, server_default="ECONOMY"
        ),
        sa.Column("total_searches", sa.Integer, nullable=False, server_default="0"),
        sa.Column("preferred_departure_time", sa.String(20), nullable=True),
        sa.Column("preferred_months", sa.Text, nullable=False, server_default="[]"),
        sa.Column(
            "preferred_currency", sa.String(3), nullable=False, server_default="USD"
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_preference_user"),
    )
    op.create_index(
        "ix_user_preference_profiles_user_id", "user_preference_profiles", ["user_id"]
    )


def downgrade() -> None:
    op.drop_table("user_preference_profiles")
    op.drop_table("chat_messages")
    op.drop_table("chat_conversations")
    op.drop_table("recommendation_logs")
    op.drop_table("prediction_history")
