from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException


def _load_key() -> bytes:
    raw = os.environ.get("TOKEN_ENCRYPTION_KEY", "")
    if not raw or raw.startswith("<"):
        # Local fallback is intentionally ephemeral. Production must set TOKEN_ENCRYPTION_KEY.
        return base64.urlsafe_b64encode(os.urandom(32))
    try:
        key = raw.encode()
        Fernet(key)
        return key
    except Exception as exc:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY must be a Fernet 32-byte urlsafe base64 key") from exc


_FERNET = Fernet(_load_key())


def encrypt_text(value: str) -> bytes:
    return _FERNET.encrypt(value.encode())


def decrypt_text(value: bytes) -> str:
    try:
        return _FERNET.decrypt(value).decode()
    except InvalidToken as exc:
        raise HTTPException(status_code=500, detail="token decryption failed; check key version") from exc
