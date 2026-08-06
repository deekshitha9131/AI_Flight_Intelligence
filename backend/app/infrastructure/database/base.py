"""Declarative base for every ORM model in the project.

Every model in app/infrastructure/database/models/ inherits from `Base`
defined here — there is exactly one declarative base for the whole
application, which is what lets `Base.metadata` describe the entire
schema in one place (Alembic's `env.py`, built in a later phase once
models exist, points at this metadata for autogeneration).

The naming convention is not cosmetic: without it, SQLAlchemy lets the
database driver assign auto-generated names to indexes, unique
constraints, and foreign keys — those names differ across dialects and
across runs, which makes Alembic's autogenerate diff unreliable (it may
see a constraint as "changed" when only its auto-assigned name changed).
Declaring the convention up front means every constraint gets a
deterministic, predictable name from the start.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# SQLAlchemy's own documented recommended convention. %(column_0_name)s
# and friends are placeholders SQLAlchemy fills in per-constraint.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Shared declarative base. All ORM models inherit from this directly
    (optionally via the mixins in app/infrastructure/database/mixins.py)."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
