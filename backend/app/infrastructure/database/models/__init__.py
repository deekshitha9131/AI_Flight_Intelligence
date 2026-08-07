"""ORM model registry.

Every SQLAlchemy model in the project must be imported here — see the
original module docstring (unchanged) for why this matters to Alembic
autogenerate.
"""

from app.infrastructure.database.models.attachment import AttachmentModel
from app.infrastructure.database.models.email import EmailModel
from app.infrastructure.database.models.oauth_token import OAuthTokenModel
from app.infrastructure.database.models.thread import ThreadModel
from app.infrastructure.database.models.user import UserModel

__all__ = ["UserModel", "OAuthTokenModel", "ThreadModel", "EmailModel", "AttachmentModel"]