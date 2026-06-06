from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet, InvalidToken


def _load_key() -> bytes:
    raw = os.environ.get("TOKEN_ENCRYPTION_KEY")
    if not raw:
        return base64.urlsafe_b64encode(b"personal-os-local-dev-key-32bytes"[:32])
    return raw.encode()


def fernet() -> Fernet:
    return Fernet(_load_key())


def encrypt_text(value: str) -> bytes:
    return fernet().encrypt(value.encode("utf-8"))


def decrypt_text(value: bytes) -> str:
    try:
        return fernet().decrypt(value).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("token decryption failed; verify TOKEN_ENCRYPTION_KEY") from exc
