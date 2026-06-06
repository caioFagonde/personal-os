from datetime import datetime, timezone

import pytest

from app.delegation import Contact, ContactChannel, DelegationRule, build_delegation_messages, connector_for_channel, validate_official_connector
from app.parser import parse_capture_command, parse_note_frontmatter, task_title_from_body
from app.tasking import follow_up_at, initial_task_status, priority_to_rank, stable_task_fingerprint


def test_parse_secretary_command_channels_due_priority_tags():
    now = datetime(2026, 6, 6, 12, tzinfo=timezone.utc)
    cmd = parse_capture_command('/secretary whatsapp email due today 17h high #admin Reschedule dentist appointment', now)
    assert cmd.target == 'secretary'
    assert cmd.channels == ['whatsapp', 'email']
    assert cmd.due_at.isoformat() == '2026-06-06T17:00:00+00:00'
    assert cmd.priority == 'high'
    assert cmd.tags == ['admin']
    assert cmd.body == 'Reschedule dentist appointment'
    assert cmd.is_delegation is True


def test_parse_task_command_is_self_inbox():
    cmd = parse_capture_command('/task due tomorrow 09:30 #reading Finish chapter 3', datetime(2026, 6, 6, 12, tzinfo=timezone.utc))
    assert cmd.target == 'self'
    assert cmd.is_delegation is False
    assert cmd.due_at.isoformat() == '2026-06-07T09:30:00+00:00'


def test_frontmatter_delegation_defaults_secretary():
    cmd = parse_note_frontmatter({'type': 'delegation', 'channels': 'wa,email', 'due': 'tomorrow', 'priority': 'urgent'}, 'Call supplier', datetime(2026, 6, 6, 12, tzinfo=timezone.utc))
    assert cmd.target == 'secretary'
    assert cmd.channels == ['whatsapp', 'email']
    assert cmd.priority == 'urgent'
    assert cmd.due_at.isoformat() == '2026-06-07T09:00:00+00:00'


def test_task_title_fingerprint_and_follow_up():
    assert task_title_from_body('Ask João for the signed contract. Then archive it.') == 'Ask João for the signed contract'
    assert priority_to_rank('urgent') == 1
    assert initial_task_status('secretary') == 'delegated'
    due = datetime(2026, 6, 6, 17, tzinfo=timezone.utc)
    assert follow_up_at(due).isoformat() == '2026-06-07T17:00:00+00:00'
    assert stable_task_fingerprint('note', '1', 'Hello  World') == stable_task_fingerprint('note', '1', 'hello world')


def test_delegation_builds_email_and_whatsapp_outbox():
    contact = Contact(
        key='secretary',
        display_name='Secretary',
        channels=[ContactChannel('email', 'sec@example.com', True), ContactChannel('whatsapp', '+5511999999999', True)],
    )
    rule = DelegationRule(target='secretary', channels=['whatsapp', 'email'], requires_approval=False)
    messages = build_delegation_messages(task_id='task-1', title='Reschedule dentist', body='Next Tuesday preferred', contact=contact, rule=rule, requested_channels=[])
    assert [m.channel for m in messages] == ['whatsapp', 'email']
    assert messages[0].connector == 'whatsapp.cloud_api'
    assert messages[1].subject == 'Delegated task: Reschedule dentist'
    assert validate_official_connector('whatsapp', 'whatsapp.cloud_api') is True
    assert validate_official_connector('whatsapp', 'browser_scraper') is False


def test_delegation_rejects_unsupported_or_missing_channel():
    contact = Contact(key='secretary', display_name='Secretary', channels=[ContactChannel('email', 'sec@example.com')])
    rule = DelegationRule(target='secretary', channels=['email'])
    with pytest.raises(ValueError):
        build_delegation_messages(task_id='1', title='T', body='B', contact=contact, rule=rule, requested_channels=['sms'])
    with pytest.raises(ValueError):
        build_delegation_messages(task_id='1', title='T', body='B', contact=contact, rule=rule, requested_channels=['whatsapp'])


def test_parse_empty_and_plain_text_capture():
    empty = parse_capture_command('   ')
    assert empty.body == ''
    plain = parse_capture_command('Remember to check the lab notebook')
    assert plain.target is None
    assert plain.body == 'Remember to check the lab notebook'


def test_parse_to_target_and_aliases_and_no_duplicate_channels():
    cmd = parse_capture_command('/capture to assistant wa zap mail normal Ask for agenda')
    assert cmd.target == 'secretary'
    assert cmd.channels == ['whatsapp', 'email']
    assert cmd.priority == 'normal'


def test_parse_due_iso_and_invalid_due_falls_to_body():
    iso = parse_capture_command('/task due 2026-06-06T18:30:00+00:00 Submit report')
    assert iso.due_at.isoformat() == '2026-06-06T18:30:00+00:00'
    invalid = parse_capture_command('/task due someday maybe')
    assert invalid.due_at is None
    assert invalid.body == 'due someday maybe'


def test_frontmatter_channel_list_datetime_and_no_type():
    due = datetime(2026, 6, 8, 10, tzinfo=timezone.utc)
    cmd = parse_note_frontmatter({'channels': ['mail', 'ntfy'], 'due_at': due, 'tags': ['ops']}, 'Just store this')
    assert cmd.target is None
    assert cmd.channels == ['email', 'ntfy']
    assert cmd.tags == ['ops']
    assert cmd.due_at == due


def test_frontmatter_bad_due_and_scalar_tags():
    cmd = parse_note_frontmatter({'due': 'not-a-date', 'tags': 'x'}, 'Body')
    assert cmd.due_at is None
    assert cmd.tags == []


def test_tasking_defaults_and_unknown_priority():
    assert priority_to_rank('weird') == 3
    created = datetime(2026, 6, 6, 12, tzinfo=timezone.utc)
    assert follow_up_at(None, created).isoformat() == '2026-06-07T12:00:00+00:00'
    assert initial_task_status(None) == 'inbox'


def test_missing_connector_validation_and_subjectless_whatsapp():
    assert validate_official_connector('sms', 'anything') is False
    contact = Contact(key='secretary', display_name='Secretary', channels=[ContactChannel('whatsapp', '+55')])
    rule = DelegationRule(target='secretary', channels=['whatsapp'], requires_approval=True)
    [message] = build_delegation_messages(task_id='1', title='Do X', body='Body', contact=contact, rule=rule, requested_channels=[])
    assert message.subject is None
    assert message.requires_approval is True
    assert 'Tracking ID: 1' in message.body


def test_due_edge_cases_and_fallback_title():
    now = datetime(2026, 6, 6, 12, tzinfo=timezone.utc)
    assert parse_capture_command('/task due', now).due_at is None
    assert parse_capture_command('/task due hoje', now).due_at.isoformat() == '2026-06-06T17:00:00+00:00'
    assert parse_capture_command('/task due tomorrow later Body', now).due_at.isoformat() == '2026-06-07T17:00:00+00:00'
    assert parse_note_frontmatter({'due': ''}, 'x', now).due_at is None
    assert parse_note_frontmatter({'due': 'today'}, 'x', now).due_at.isoformat() == '2026-06-06T17:00:00+00:00'
    assert parse_note_frontmatter({'due': 'tomorrow 16h'}, 'x', now).due_at.isoformat() == '2026-06-07T16:00:00+00:00'
    assert task_title_from_body('   ', 'Fallback') == 'Fallback'


def test_to_token_does_not_override_existing_unknown_target():
    cmd = parse_capture_command('/secretary to stranger body text')
    assert cmd.target == 'secretary'
    assert cmd.body == 'to stranger body text'


def test_alias_normalization_in_contact_channels_and_source_note_message():
    contact = Contact(key='secretary', display_name='Secretary', channels=[ContactChannel('wa', '+55'), ContactChannel('mail', 's@example.com')])
    rule = DelegationRule(target='secretary', channels=['zap', 'mail'])
    messages = build_delegation_messages(task_id='x', title='Title', body='Body', contact=contact, rule=rule, requested_channels=[], source_note_id='note-1')
    assert [m.channel for m in messages] == ['whatsapp', 'email']
    assert 'Source note: note-1' in messages[0].body


def test_follow_up_naive_datetime_is_normalized():
    due = datetime(2026, 6, 6, 17)
    assert follow_up_at(due).tzinfo is not None


def test_twilio_whatsapp_provider_is_supported_without_replacing_meta_cloud_api():
    contact = Contact(key='secretary', display_name='Secretary', channels=[ContactChannel('whatsapp', '+5511999999999')])
    rule = DelegationRule(target='secretary', channels=['whatsapp'], requires_approval=False)
    [sandbox] = build_delegation_messages(task_id='tw-1', title='Ping', body='Body', contact=contact, rule=rule, requested_channels=[], whatsapp_provider='twilio_sandbox')
    assert sandbox.connector == 'whatsapp.twilio_sandbox'
    assert connector_for_channel('whatsapp', 'twilio') == 'whatsapp.twilio'
    assert validate_official_connector('whatsapp', 'whatsapp.twilio_sandbox', 'twilio_sandbox') is True
    assert validate_official_connector('whatsapp', 'whatsapp.cloud_api', 'cloud_api') is True
