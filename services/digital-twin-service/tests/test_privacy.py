from datetime import datetime, timedelta, timezone

from app.privacy import allowed_for_purpose, classify_sensitivity, is_expired, redact_text, sanitize_memory_record


def test_classify_sensitive_and_restricted_content():
    assert classify_sensitivity("email me at person@example.com") == "personal"
    assert classify_sensitivity("api_" + "key=abc123") == "restricted"
    assert classify_sensitivity("blood pressure", tags=["health"]) == "sensitive"
    assert classify_sensitivity("anything", declared="public") == "public"


def test_redaction_removes_external_identifiers():
    text = redact_text("to" + "ken=abc call +55 11 99999-9999 or me@example.com")
    assert "abc" not in text
    assert "<phone>" in text
    assert "<email>" in text


def test_retention_expiry_by_memory_class():
    old = datetime.now(timezone.utc) - timedelta(days=8)
    assert is_expired("ephemeral", old)
    assert not is_expired("working", old)
    assert not is_expired("archival", old)


def test_purpose_policy_blocks_sensitive_recommendations_by_default():
    ok, reason = allowed_for_purpose({"digital_twin:read", "recommendations:write"}, "recommendation", "sensitive")
    assert not ok
    assert "sensitive" in reason
    ok, _ = allowed_for_purpose({"digital_twin:read", "recommendations:write"}, "recommendation", "sensitive", {"allow_sensitive_recommendations": True})
    assert ok


def test_sanitize_memory_record_redacts_output():
    record = {"content": "secret=abc person@example.com", "summary": "call +1 555 555 5555"}
    out = sanitize_memory_record(record)
    assert "abc" not in out["content"]
    assert "<email>" in out["content"]


def test_plain_text_and_non_external_redaction_and_long_term_deadline():
    assert classify_sensitivity('plain journal text') == 'personal'
    assert classify_sensitivity('') == 'public'
    assert redact_text('person@example.com', external=False) == 'person@example.com'
    old = datetime.now(timezone.utc) - timedelta(days=1000)
    assert not is_expired('long_term', old)


def test_naive_datetime_and_missing_scope_and_export_policy():
    old_naive = (datetime.now(timezone.utc) - timedelta(days=8)).replace(tzinfo=None)
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    assert is_expired('ephemeral', old_naive, now_naive)
    ok, reason = allowed_for_purpose(set(), 'search', 'personal')
    assert not ok and 'missing scopes' in reason
    ok, reason = allowed_for_purpose({'digital_twin:export'}, 'export', 'restricted')
    assert not ok and 'restricted' in reason
    ok, _ = allowed_for_purpose({'digital_twin:export'}, 'export', 'restricted', {'allow_restricted_export': True})
    assert ok


def test_sanitize_can_skip_redaction_by_policy():
    record = {'content': 'person@example.com'}
    out = sanitize_memory_record(record, {'redact_external_outputs': False})
    assert out['content'] == 'person@example.com'
