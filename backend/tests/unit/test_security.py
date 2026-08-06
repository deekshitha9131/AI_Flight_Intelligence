"""Tests for app/core/security.py."""

import pytest

from app.core.config import Settings
from app.core.security import TokenCipher, TokenCipherError

BASE_ENV = {
    "APP_ENV": "development",
    "APP_DEBUG": "true",
    "APP_SECRET_KEY": "dev-secret",
    "DATABASE_URL": "postgresql+asyncpg://u:p@h:5432/d",
    "REDIS_URL": "redis://h:6379/0",
    "CELERY_BROKER_URL": "redis://h:6379/1",
    "CELERY_RESULT_BACKEND": "redis://h:6379/1",
    "TOKEN_ENCRYPTION_KEY": "test-token-encryption-key-value",
    "CORS_ORIGINS": "http://localhost:5173",
}


def _settings(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> Settings:
    env = {**BASE_ENV, **overrides}
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_encrypt_produces_different_bytes_than_plaintext(monkeypatch: pytest.MonkeyPatch) -> None:
    cipher = TokenCipher(_settings(monkeypatch))
    ciphertext = cipher.encrypt("ya29.fake_access_token")
    assert ciphertext != b"ya29.fake_access_token"


def test_encrypt_decrypt_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    cipher = TokenCipher(_settings(monkeypatch))
    plaintext = "1//fake_refresh_token_value"
    assert cipher.decrypt(cipher.encrypt(plaintext)) == plaintext


def test_tampered_ciphertext_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    cipher = TokenCipher(_settings(monkeypatch))
    ciphertext = cipher.encrypt("some-token")
    tampered = ciphertext[:-5] + b"xxxxx"

    with pytest.raises(TokenCipherError):
        cipher.decrypt(tampered)


def test_wrong_key_cannot_decrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    cipher_a = TokenCipher(_settings(monkeypatch, TOKEN_ENCRYPTION_KEY="key-a-value"))
    ciphertext = cipher_a.encrypt("some-token")

    cipher_b = TokenCipher(_settings(monkeypatch, TOKEN_ENCRYPTION_KEY="key-b-value"))
    with pytest.raises(TokenCipherError):
        cipher_b.decrypt(ciphertext)


def test_same_key_derived_deterministically(monkeypatch: pytest.MonkeyPatch) -> None:
    """A token encrypted by one process instance must be decryptable by
    another instance built from the same configured key — this is what
    makes stored tokens survive an application restart."""
    cipher_1 = TokenCipher(_settings(monkeypatch))
    cipher_2 = TokenCipher(_settings(monkeypatch))

    ciphertext = cipher_1.encrypt("survives-a-restart")
    assert cipher_2.decrypt(ciphertext) == "survives-a-restart"
