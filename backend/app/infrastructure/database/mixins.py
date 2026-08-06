"""Reusable ORM mixins.

Per the frozen database design: every table gets a UUID surrogate
primary key, and every table gets `created_at`/`updated_at`. Some
user-facing tables additionally get a nullable `deleted_at` for soft
deletion. Rather than repeating these columns on every model, they're
defined once here as mixins — a model composes the ones it needs:

    class Draft(Base, UUIDPrimaryKeyMixin, TimestampMixin):
        ...

    class User(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
        ...
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """Adds a UUID surrogate primary key, generated client-side.

    Generated in Python (`default=uuid.uuid4`) rather than via a
    Postgres server-side default (e.g. `gen_random_uuid()`) so the ID is
    known immediately after constructing the object, before any INSERT
    happens — useful for referencing a new entity's ID within the same
    unit of work before commit, and it avoids requiring the `pgcrypto`
    extension purely for ID generation.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """Adds `created_at` / `updated_at`, both server-generated.

    Using `server_default=func.now()` (rather than a Python-side
    default) means the timestamp is assigned by PostgreSQL at insert
    time — correct even under clock skew between application
    processes, and correct for rows inserted by something other than
    this application (a manual migration, a psql session) too.
    `onupdate=func.now()` makes `updated_at` self-maintaining: no
    service method ever has to remember to bump it by hand.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Adds a nullable `deleted_at` for soft deletion.

    Applied only to user-facing entities where recoverability matters
    (per the frozen schema design) — append-only audit/history tables
    never use this, since they are never deleted at all, soft or
    otherwise.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
