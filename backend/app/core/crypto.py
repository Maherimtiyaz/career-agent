"""Fernet encryption helpers for BYOK (bring-your-own-key) storage.

Used to encrypt per-user API keys at rest. The master key lives in
ENCRYPTION_KEY (backend/.env, gitignored). If ENCRYPTION_KEY is missing
or malformed, calls fail loudly rather than silently storing plaintext.

Generate a key with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class EncryptionError(RuntimeError):
    """Raised when encryption/decryption cannot proceed."""


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = get_settings().encryption_key
    if not key:
        raise EncryptionError(
            "ENCRYPTION_KEY is not set. Generate one with "
            "`python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\"` and add it to backend/.env"
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:
        raise EncryptionError(
            "ENCRYPTION_KEY is malformed. It must be a URL-safe base64 "
            "32-byte key produced by Fernet.generate_key()."
        ) from exc


def encrypt_api_key(plain: str) -> str:
    """Encrypt a plaintext API key. Raises EncryptionError on empty input."""
    if not plain:
        raise EncryptionError("Cannot encrypt an empty API key")
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_api_key(token: str) -> str:
    """Decrypt a token produced by encrypt_api_key."""
    if not token:
        raise EncryptionError("Cannot decrypt an empty token")
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise EncryptionError(
            "Token is invalid or was encrypted with a different key"
        ) from exc


def generate_encryption_key() -> str:
    """Convenience wrapper — same output as Fernet.generate_key()."""
    return Fernet.generate_key().decode("utf-8")
