from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_ai_understanding",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("intent", sa.String(length=32), nullable=False),
        sa.Column("urgency", sa.String(length=32), nullable=False),
        sa.Column("sentiment", sa.String(length=32), nullable=False),
        sa.Column(
            "entities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_email_ai_understanding"),
        sa.UniqueConstraint("email_id", name="uq_email_ai_understanding_email_id"),
        sa.ForeignKeyConstraint(
            ["email_id"],
            ["emails.id"],
            name="fk_email_ai_understanding_email_id_emails",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_email_ai_understanding_email_id", "email_ai_understanding", ["email_id"])


def downgrade() -> None:
    op.drop_index("ix_email_ai_understanding_email_id", table_name="email_ai_understanding")
    op.drop_table("email_ai_understanding")