#!/usr/bin/env python3
from __future__ import annotations
import base64
import secrets
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else ".env")
text = path.read_text()
password = secrets.token_urlsafe(24)
replacements = {
    "<generate-a-local-password>": password,
    "<generate-minio-user>": "minioadmin_" + secrets.token_hex(4),
    "<generate-minio-password>": secrets.token_urlsafe(32),
    "<generate-with-openssl-rand-hex-32>": secrets.token_hex(32),
    "<generate-32-byte-base64-key>": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
}
for k, v in replacements.items():
    text = text.replace(k, v)
# Keep DATABASE_URL consistent with generated password.
lines = []
for line in text.splitlines():
    if line.startswith("DATABASE_URL="):
        line = f"DATABASE_URL=postgresql://personal_os:{password}@postgres:5432/personal_os"
    lines.append(line)
path.write_text("\n".join(lines) + "\n")
print(f"generated local secrets in {path}")
