from datetime import datetime, timedelta, timezone

from app.n8n_bridge import normalize_n8n_webhook, sign_payload, verify_payload_signature
from app.notifications import build_notification, render_template
from app.scheduler import is_interval_due, next_interval_due, stable_jitter_seconds


def test_interval_due_and_next_due():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    last = now - timedelta(seconds=60)
    assert is_interval_due(last, 30, now=now)
    assert not is_interval_due(last, 120, now=now)
    assert next_interval_due(last, 30, now=now) == last + timedelta(seconds=30)


def test_stable_jitter_bounds():
    assert 0 <= stable_jitter_seconds("workflow-a", 30) <= 30
    assert stable_jitter_seconds("workflow-a", 30) == stable_jitter_seconds("workflow-a", 30)


def test_n8n_signature_roundtrip():
    payload = {"event": "study.session.completed", "score": 1}
    sig = sign_payload(payload, "secret", timestamp=1000)
    assert verify_payload_signature(payload, sig, "secret", now=1000)
    assert not verify_payload_signature(payload, sig, "wrong", now=1000)
    assert not verify_payload_signature(payload, sig, "secret", now=5000)


def test_n8n_normalization_idempotency_key_stable():
    payload = {"event": "x", "a": 1}
    one = normalize_n8n_webhook(payload)
    two = normalize_n8n_webhook(payload)
    assert one.event_type == "x"
    assert one.idempotency_key == two.idempotency_key


def test_notification_rendering_and_clamping():
    assert render_template("Hello $name", {"name": "Caio"}) == "Hello Caio"
    notification = build_notification("topic", "T" * 200, "M", priority="invalid")
    assert notification["priority"] == "default"
    assert len(notification["title"]) == 160
