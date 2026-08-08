from sqlalchemy import BigInteger
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums.user_status import UserStatus
from app.infrastructure.database.base import Base
from app.infrastructure.database.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class UserModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    

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
    
    gmail_history_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)