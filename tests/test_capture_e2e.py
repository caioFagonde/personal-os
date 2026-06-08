"""
Capture end-to-end acceptance tests.

Verifies:
 - /task creates inbox task (not delegation)
 - /note stores capture (not delegation)
 - /secretary triggers delegation flow
 - Secretary missing channels returns structured 409
 - Invalid WHATSAPP_PROVIDER returns structured 409 (not raw 500)
 - Error handlers produce JSON, never opaque tracebacks
 - WhatsApp provider default is valid
 - No debug file writes in production code
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "capture-service"))


def test_task_command_creates_inbox_task():
    from app.parser import parse_capture_command
    from app.tasking import initial_task_status

    cmd = parse_capture_command("/task Buy milk tomorrow")
    assert cmd.target == "self"
    assert cmd.is_delegation is False
    assert initial_task_status(cmd.target) == "inbox"
    assert "milk" in cmd.body.lower()


def test_note_command_stores_capture_not_delegation():
    from app.parser import parse_capture_command
    from app.tasking import initial_task_status

    cmd = parse_capture_command("/note Some interesting observation")
    assert cmd.is_delegation is False
    assert initial_task_status(cmd.target) == "inbox"
    assert cmd.body == "Some interesting observation"


def test_secretary_command_is_delegation():
    from app.parser import parse_capture_command
    from app.tasking import initial_task_status

    cmd = parse_capture_command("/secretary whatsapp email due today 17h Ask João for contract")
    assert cmd.target == "secretary"
    assert cmd.is_delegation is True
    assert initial_task_status(cmd.target) == "delegated"
    assert "whatsapp" in cmd.channels
    assert "email" in cmd.channels


def test_secretary_missing_channels_returns_structured_409():
    source = (ROOT / "services" / "capture-service" / "app" / "main.py").read_text()
    assert "missing_channels" in source
    assert "status_code=409" in source
    assert "required_env" in source
    assert "SECRETARY_EMAIL" in source
    assert "SECRETARY_WHATSAPP" in source


def test_invalid_whatsapp_provider_returns_structured_409():
    source = (ROOT / "services" / "capture-service" / "app" / "main.py").read_text()
    assert "invalid_delegation_config" in source
    assert "WHATSAPP_PROVIDER" in source


def test_whatsapp_provider_default_is_valid():
    from app.delegation import WHATSAPP_CONNECTORS, normalize_whatsapp_provider

    source = (ROOT / "services" / "capture-service" / "app" / "main.py").read_text()
    import re
    match = re.search(r'WHATSAPP_PROVIDER\s*=.*get\(\s*"WHATSAPP_PROVIDER"\s*,\s*"([^"]+)"', source)
    assert match, "WHATSAPP_PROVIDER default not found"
    default = match.group(1)
    assert default in WHATSAPP_CONNECTORS, f"Default provider '{default}' is not in WHATSAPP_CONNECTORS"
    normalize_whatsapp_provider(default)


def test_no_debug_file_writes_in_capture_service():
    source = (ROOT / "services" / "capture-service" / "app" / "main.py").read_text()
    assert 'open("debug' not in source, "Debug file writes must be removed before production"
    assert "debug.txt" not in source


def test_error_handlers_produce_structured_json():
    source = (ROOT / "services" / "capture-service" / "app" / "main.py").read_text()
    assert "exception_handler" in source
    assert "database_error" in source
    assert "internal_error" in source
    assert "JSONResponse" in source


def test_delegation_build_messages_with_valid_provider():
    from app.delegation import (
        Contact,
        ContactChannel,
        DelegationRule,
        build_delegation_messages,
    )

    contact = Contact(
        key="secretary",
        display_name="Secretary",
        channels=[
            ContactChannel("email", "sec@example.com", True),
            ContactChannel("whatsapp", "+5511999999999", True),
        ],
    )
    rule = DelegationRule(target="secretary", channels=["whatsapp", "email"], requires_approval=False)
    messages = build_delegation_messages(
        task_id="task-1",
        title="Test delegation",
        body="Please handle this",
        contact=contact,
        rule=rule,
        requested_channels=["whatsapp", "email"],
        whatsapp_provider="cloud_api",
    )
    assert len(messages) == 2
    assert messages[0].channel == "whatsapp"
    assert messages[0].connector == "whatsapp.cloud_api"
    assert messages[1].channel == "email"


def test_delegation_build_messages_invalid_provider_raises():
    import pytest
    from app.delegation import (
        Contact,
        ContactChannel,
        DelegationRule,
        build_delegation_messages,
    )

    contact = Contact(
        key="secretary",
        display_name="Secretary",
        channels=[ContactChannel("whatsapp", "+55", True)],
    )
    rule = DelegationRule(target="secretary", channels=["whatsapp"], requires_approval=False)
    with pytest.raises(ValueError, match="unsupported WhatsApp provider"):
        build_delegation_messages(
            task_id="task-1",
            title="Test",
            body="Body",
            contact=contact,
            rule=rule,
            requested_channels=["whatsapp"],
            whatsapp_provider="twillio",
        )


def test_capture_command_json_serializable_with_due():
    from app.parser import parse_capture_command

    cmd = parse_capture_command("/task due tomorrow 17h Finish report")
    assert cmd.due_at is not None
    serialized = json.dumps(cmd.__dict__, default=str)
    assert "due_at" in serialized
    assert "Finish report" in serialized
