import base64

import pytest

from app.providers import gmail_raw_message, normalize_whatsapp_address, twilio_message_payload
from app.worker import WorkerConfig, retry_delay_sql


def test_gmail_raw_message_is_base64url_rfc_message():
    raw = gmail_raw_message(to="secretary@example.com", subject="Task", body="Please handle this.")
    padded = raw + "=" * (-len(raw) % 4)
    decoded = base64.urlsafe_b64decode(padded.encode()).decode()
    assert "To: secretary@example.com" in decoded
    assert "Subject: Task" in decoded
    assert "Please handle this." in decoded


def test_retry_delay_sql_is_bounded_case_expression():
    sql = retry_delay_sql()
    assert "CASE" in sql
    assert "6 hours" in sql
    assert "attempts" in sql


def test_worker_config_has_safe_defaults():
    cfg = WorkerConfig(execute=False)
    assert cfg.limit == 25
    assert cfg.max_attempts == 5


def test_twilio_payload_rejects_malformed_numbers():
    with pytest.raises(ValueError):
        normalize_whatsapp_address("1155963255206")
    payload = twilio_message_payload(to="+5511999999999", body="ok", from_="whatsapp:+14155238886")
    assert payload["To"] == "whatsapp:+5511999999999"
