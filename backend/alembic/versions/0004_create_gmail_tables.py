from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "threads",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("gmail_thread_id", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("history_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_threads"),
        sa.UniqueConstraint("user_id", "gmail_thread_id", name="uq_threads_user_id_gmail_thread_id"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_threads_user_id_users", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_threads_user_id", "threads", ["user_id"])

    op.create_table(
        "emails",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("gmail_message_id", sa.String(length=64), nullable=False),
        sa.Column("sender", sa.String(length=255), nullable=False),
        sa.Column("recipients", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("cc", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("bcc", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_starred", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("has_attachments", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("label_ids", sa.ARRAY(sa.String()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_emails"),
        sa.UniqueConstraint(
            "user_id", "gmail_message_id", name="uq_emails_user_id_gmail_message_id"
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["threads.id"], name="fk_emails_thread_id_threads", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_emails_user_id_users", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_emails_thread_id", "emails", ["thread_id"])
    op.create_index("ix_emails_user_id", "emails", ["user_id"])

    op.create_table(
        "attachments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email_id", sa.UUID(), nullable=False),
        sa.Column("gmail_attachment_id", sa.String(length=255), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id", name="pk_attachments"),
        sa.UniqueConstraint(
            "email_id", "gmail_attachment_id", name="uq_attachments_email_id_gmail_attachment_id"
        ),
        sa.ForeignKeyConstraint(
            ["email_id"], ["emails.id"], name="fk_attachments_email_id_emails", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_attachments_email_id", "attachments", ["email_id"])


def downgrade() -> None:
    op.drop_table("attachments")
    op.drop_table("emails")
    op.drop_table("threads")