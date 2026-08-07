"""User ORM model.

The persistence-only representation of a user — SQLAlchemy-specific,
mapped to/from the framework-agnostic domain entity
(app/domain/entities/user.py) by UserRepository
(app/infrastructure/database/repositories/user_repository.py). Nothing
outside that repository should ever import this class directly;
services and routers work with the domain entity.
"""

from sqlalchemy import BigInteger
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums.user_status import UserStatus
from app.infrastructure.database.base import Base
from app.infrastructure.database.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class UserModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Maps to the `users` table. See docs/architecture/02-system-design.md
    for the frozen schema this table originates from — this model
    currently implements the subset of that schema this phase requires
    (email, identity, status); `plan_tier`, `llm_token_budget_daily`,
    and `onboarding_completed_at` are documented there but not yet
    needed by any built feature, so they're deferred rather than added
    speculatively."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    google_sub_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[UserStatus] = mapped_column(
    SQLEnum(
        UserStatus,
        name="user_status",
        native_enum=True,
        values_callable=lambda enum: [member.value for member in enum],
    ),
    nullable=False,
    default=UserStatus.ACTIVE,
    server_default=UserStatus.ACTIVE.value,
)
    # NULL means "no Gmail initial sync has ever completed for this
    # user" — GmailService.sync_incremental uses that exact condition
    # to require an initial sync first (Task 3.4). Deliberately not
    # part of the framework-agnostic User domain entity — see
    # UserRepository.get_gmail_history_id/update_gmail_history_id for
    # why this is exposed as two narrow methods instead, the same
    # pattern already used for oauth_tokens.
    gmail_history_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)