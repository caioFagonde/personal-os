#!/usr/bin/env python3
from __future__ import annotations

import base64
import re
import secrets
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else ".env")
text = path.read_text()
password = secrets.token_urlsafe(24)

key_generators = {
    "POSTGRES_PASSWORD": lambda: password,
    "DATABASE_URL": lambda: f"postgresql://personal_os:{password}@postgres:5432/personal_os",
    "MINIO_ROOT_USER": lambda: "minioadmin_" + secrets.token_hex(4),
    "MINIO_ROOT_PASSWORD": lambda: secrets.token_urlsafe(32),
    "JWT_SECRET": lambda: secrets.token_hex(32),
    "DEVICE_SIGNING_SECRET": lambda: secrets.token_hex(32),
    "COMMAND_SIGNING_SECRET": lambda: secrets.token_hex(32),
    "N8N_WEBHOOK_SECRET": lambda: secrets.token_hex(32),
    "TOKEN_ENCRYPTION_KEY": lambda: base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    "SERVICE_TOKEN_SECRET": lambda: secrets.token_hex(32),
}

def replace_line(line: str) -> str:
    if "=" not in line or line.startswith("#"):
        return line
    key, _, value = line.partition("=")
    if "<generate" in value and key in key_generators:
        return f"{key}={key_generators[key]()}"
    return line

lines = [replace_line(line) for line in text.splitlines()]
text = "\n".join(lines) + "\n"
# Defensive cleanup for any historical placeholder style left behind.
text = re.sub(r"<generate-minio-user>", "minioadmin_" + secrets.token_hex(4), text)
text = re.sub(r"<generate-minio-password>", secrets.token_urlsafe(32), text)
text = re.sub(r"<generate-a-local-password>", password, text)
text = re.sub(r"<generate-with-openssl-rand-hex-32>", lambda _m: secrets.token_hex(32), text)
text = re.sub(r"<generate-32-byte-base64-key>", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(), text)
text = re.sub(r"replace-with-generated-service-token-secret", secrets.token_hex(32), text)
path.write_text(text)
print(f"generated local secrets in {path}")
