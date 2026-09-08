from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

from app.core.constants import EMBEDDING_DIMENSIONS

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email_id", sa.UUID(), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_email_chunks"),
        sa.UniqueConstraint(
            "email_id", "chunk_index", name="uq_email_chunks_email_id_chunk_index"
        ),
        sa.ForeignKeyConstraint(
            ["email_id"], ["emails.id"], name="fk_email_chunks_email_id_emails", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["threads.id"],
            name="fk_email_chunks_thread_id_threads",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_email_chunks_user_id_users", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_email_chunks_email_id", "email_chunks", ["email_id"])
    op.create_index("ix_email_chunks_thread_id", "email_chunks", ["thread_id"])
    op.create_index("ix_email_chunks_user_id", "email_chunks", ["user_id"])
    op.execute(
        "CREATE INDEX ix_email_chunks_embedding_cosine ON email_chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_email_chunks_embedding_cosine")
    op.drop_index("ix_email_chunks_user_id", table_name="email_chunks")
    op.drop_index("ix_email_chunks_thread_id", table_name="email_chunks")
    op.drop_index("ix_email_chunks_email_id", table_name="email_chunks")
    op.drop_table("email_chunks")