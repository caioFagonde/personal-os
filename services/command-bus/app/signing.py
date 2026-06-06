from __future__ import annotations

import hashlib
import hmac
import json


def verify_signature(params: dict, signature: str, secret: str) -> bool:
    body = json.dumps(params, sort_keys=True, separators=(",", ":")).encode()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
