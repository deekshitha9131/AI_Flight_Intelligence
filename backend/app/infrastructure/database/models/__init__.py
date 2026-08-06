"""ORM model registry.

Every SQLAlchemy model in the project must be imported here, e.g.:

    from app.infrastructure.database.models.draft import Draft
    from app.infrastructure.database.models.thread import Thread

This is not organizational preference — alembic/env.py imports this
package specifically so `Base.metadata` is fully populated before
`alembic revision --autogenerate` diffs it against the live database. A
model defined but never imported here is invisible to autogenerate and
will be silently treated as if it doesn't exist.
"""

from app.infrastructure.database.models.oauth_token import OAuthTokenModel
from app.infrastructure.database.models.user import UserModel

__all__ = ["UserModel", "OAuthTokenModel"]
