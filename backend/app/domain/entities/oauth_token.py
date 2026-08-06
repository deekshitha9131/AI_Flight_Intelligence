"""OAuthToken domain entity.

Holds plaintext tokens — encryption-at-rest is a persistence detail
(see app/infrastructure/database/repositories/user_repository.py's use
of TokenCipher), not something the domain layer should know about. A
service working with a user's tokens (e.g. a future Gmail sync task)
should never have to think about ciphertext; it asks the repository for
an OAuthToken and gets a usable access_token string back.
"""

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
