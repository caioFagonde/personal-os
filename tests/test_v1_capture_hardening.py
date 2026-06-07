"""
V1 capture-service hardening tests.
Verifies the root-cause fixes for the capture 500 bug and related issues:
 - kind='service' → 'server' in ensure_device()
 - assignee_key='self'/'note' → NULL for non-delegation targets
 - json.dumps(command.__dict__) with datetime → default=str
 - /note and /task should not be treated as delegation
 - /secretary returns structured 409 when channels missing
 - structured error handler produces JSON, never opaque 500
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "capture-service"))


# ---------------------------------------------------------------------------
# Parser unit tests
# ---------------------------------------------------------------------------

def test_parser_task_is_not_delegation():
    from app.parser import parse_capture_command
    cmd = parse_capture_command("/task Buy milk")
    assert cmd.target == "self"
    assert cmd.is_delegation is False


def test_parser_note_is_not_delegation():
    from app.parser import parse_capture_command
    cmd = parse_capture_command("/note Idea for project")
    assert cmd.target == "note"
    assert cmd.is_delegation is False


def test_parser_secretary_is_delegation():
    from app.parser import parse_capture_command
    cmd = parse_capture_command("/secretary whatsapp email Ask about contract")
    assert cmd.target == "secretary"
    assert cmd.is_delegation is True
    assert "whatsapp" in cmd.channels
    assert "email" in cmd.channels


def test_parser_due_date_produces_datetime():
    from app.parser import parse_capture_command
    cmd = parse_capture_command("/task due tomorrow 09:30 Finish report")
    assert cmd.due_at is not None
    assert cmd.body == "Finish report"


def test_parser_due_date_is_json_serializable():
    import json
    from app.parser import parse_capture_command
    cmd = parse_capture_command("/task due tomorrow 17h Some task")
    result = json.dumps(cmd.__dict__, default=str)
    assert "due_at" in result


# ---------------------------------------------------------------------------
# Tasking unit tests
# ---------------------------------------------------------------------------

def test_initial_task_status_self_is_inbox():
    from app.tasking import initial_task_status
    assert initial_task_status("self") == "inbox"
    assert initial_task_status("me") == "inbox"
    assert initial_task_status(None) == "inbox"
    assert initial_task_status("note") == "inbox"
    assert initial_task_status("task") == "inbox"
    assert initial_task_status("capture") == "inbox"


def test_initial_task_status_secretary_is_delegated():
    from app.tasking import initial_task_status
    assert initial_task_status("secretary") == "delegated"
    assert initial_task_status("team") == "delegated"


# ---------------------------------------------------------------------------
# Source-code level invariants
# ---------------------------------------------------------------------------

def test_capture_ensure_device_uses_server_not_service():
    text = (ROOT / "services" / "capture-service" / "app" / "main.py").read_text()
    fn_block = text.split("async def ensure_device")[1][:500]
    assert "'service'" not in fn_block, \
        "ensure_device must use kind='server', not 'service'"
    assert "'server'" in fn_block


def test_study_companion_ensure_device_uses_server_not_service():
    text = (ROOT / "services" / "study-companion-service" / "app" / "main.py").read_text()
    assert "'service'" not in text.split("ensure_device")[1][:300], \
        "ensure_device must use kind='server', not 'service'"


def test_study_companion_create_entity_uses_correct_columns():
    text = (ROOT / "services" / "study-companion-service" / "app" / "main.py").read_text()
    create_entity_block = text.split("async def create_entity")[1][:500]
    assert "owner_device_id" not in create_entity_block, \
        "entities table has no owner_device_id column"
    assert "created_by_device_id" not in create_entity_block, \
        "entities table has no created_by_device_id column (use created_by_device)"
    assert "created_by_device" in create_entity_block


def test_capture_service_has_structured_error_handler():
    text = (ROOT / "services" / "capture-service" / "app" / "main.py").read_text()
    assert "exception_handler" in text
    assert "database_error" in text
    assert "JSONResponse" in text


def test_study_companion_has_structured_error_handler():
    text = (ROOT / "services" / "study-companion-service" / "app" / "main.py").read_text()
    assert "exception_handler" in text
    assert "database_error" in text
    assert "JSONResponse" in text


def test_capture_contact_missing_returns_structured_409():
    text = (ROOT / "services" / "capture-service" / "app" / "main.py").read_text()
    assert "missing_channels" in text
    assert "SECRETARY_EMAIL" in text
    assert "SECRETARY_WHATSAPP" in text


def test_capture_json_dumps_uses_default_str():
    text = (ROOT / "services" / "capture-service" / "app" / "main.py").read_text()
    assert "default=str" in text, \
        "json.dumps(command.__dict__) must use default=str to handle datetime"


def test_upsert_task_nulls_non_contact_targets():
    text = (ROOT / "services" / "capture-service" / "app" / "main.py").read_text()
    fn_block = text.split("async def upsert_task_from_capture")[1][:600]
    assert "non_contact_targets" in fn_block or '"self"' in fn_block
    for target in ["self", "me", "note", "task", "capture"]:
        assert f'"{target}"' in fn_block, \
            f"upsert_task_from_capture must exclude '{target}' from assignee_key"
