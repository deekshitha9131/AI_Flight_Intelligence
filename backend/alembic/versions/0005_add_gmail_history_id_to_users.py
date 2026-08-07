"""add gmail_history_id to users

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-06

Hand-written, consistent with 0001-0004. Nullable BIGINT — NULL means
"no initial sync has completed yet," which is exactly the signal
GmailService.sync_incremental uses to require an initial sync first
(see GmailSyncRequiredError in app/domain/exceptions/gmail.py). Stored
as BIGINT (not a string column) per the Task 3.4 architecture doc;
Gmail's `historyId` values are numeric despite being JSON strings on
the wire — UserRepository converts at the persistence boundary, the
same way TokenCipher handles encryption there rather than exposing it
to callers.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("gmail_history_id", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "gmail_history_id")