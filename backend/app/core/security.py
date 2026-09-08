import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings


class TokenCipherError(Exception):
    """Raised when encrypted token data cannot be decrypted."""


def _derive_fernet_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class TokenCipher:
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
