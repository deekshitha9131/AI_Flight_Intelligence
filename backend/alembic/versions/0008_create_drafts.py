"""create drafts table

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-11

Hand-written, consistent with 0001-0007. `status` is a native Postgres
enum (draft_status), matching the pattern 0002 already established for
user_status — see app/domain/enums/draft_status.py's module docstring
for why drafts (a fixed-transition state machine) get this treatment
while AI-classification columns (Task 5.6) deliberately do not.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

draft_status_enum = sa.Enum("generated", "approved", "rejected", "sent", name="draft_status")


def upgrade() -> None:
    op.create_table(
        "drafts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email_id", sa.UUID(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status",
            draft_status_enum,
            nullable=False,
            server_default="generated",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_drafts"),
        sa.ForeignKeyConstraint(
            ["email_id"], ["emails.id"], name="fk_drafts_email_id_emails", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_drafts_email_id", "drafts", ["email_id"])


def downgrade() -> None:
    op.drop_index("ix_drafts_email_id", table_name="drafts")
    op.drop_table("drafts")
    draft_status_enum.drop(op.get_bind(), checkfirst=True)