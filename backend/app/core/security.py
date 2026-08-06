"""Token encryption.

OAuth access/refresh tokens are encrypted at rest (per the frozen
security strategy — "OAuth tokens encrypted at rest") using Fernet
(AES-128-CBC + HMAC, from the `cryptography` package) — authenticated
encryption, so tampering with a stored ciphertext is detected on
decrypt, not silently accepted.

Fernet requires a 32-byte, URL-safe base64-encoded key. The configured
`TOKEN_ENCRYPTION_KEY` setting is an arbitrary-length operator-chosen
string (validated elsewhere to be non-trivial — see
app/core/config.py's production safety checks), not necessarily in that
exact format. `_derive_fernet_key` deterministically derives a
valid Fernet key from it via SHA-256 (same input secret always
produces the same key, which is required — encrypted tokens from a
previous run must still decrypt after a process restart).
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings


class TokenCipherError(Exception):
    """Raised when decryption fails — either the ciphertext was tampered
    with, or it was encrypted under a different TOKEN_ENCRYPTION_KEY
    than the one currently configured."""


def _derive_fernet_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class TokenCipher:
    """Encrypts/decrypts short strings (OAuth tokens) for storage.

    Constructed once from Settings and reused — Fernet itself is
    stateless and thread-safe, so there's no reason to rebuild it per
    call the way a fresh DB session is rebuilt per request.
    """

    def __init__(self, settings: Settings) -> None:
        self._fernet = Fernet(_derive_fernet_key(settings.token_encryption_key))

    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode("utf-8"))

    def decrypt(self, ciphertext: bytes) -> str:
        try:
            return self._fernet.decrypt(ciphertext).decode("utf-8")
        except InvalidToken as exc:
            raise TokenCipherError(
                "Failed to decrypt token — ciphertext is invalid, was tampered "
                "with, or was encrypted under a different TOKEN_ENCRYPTION_KEY."
            ) from exc
