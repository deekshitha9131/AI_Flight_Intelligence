from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID


@dataclass
class OAuthToken:
    user_id: UUID
    access_token: str
    refresh_token: str
    token_expiry: datetime
    granted_scopes: list[str]

    @property
    def is_expired(self) -> bool:
        return datetime.now(UTC) >= self.token_expiry
