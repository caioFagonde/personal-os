import hashlib
import hmac
import json

from app.signing import verify_signature


def test_command_signature_verification():
    secret = "unit-test-secret"
    params = {"project": "demo", "action": "status"}
    body = json.dumps(params, sort_keys=True, separators=(",", ":")).encode()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_signature(params, expected, secret)
    assert not verify_signature(params, "00" * 32, secret)


def test_signature_is_key_order_independent():
    secret = "unit-test-secret"
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}
    body = json.dumps(left, sort_keys=True, separators=(",", ":")).encode()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_signature(right, expected, secret)
