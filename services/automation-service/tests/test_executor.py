from app.executor import execute_workflow_plan
from app.models import WorkflowSpec


def test_execute_simple_workflow_success():
    spec = WorkflowSpec.model_validate({
        "name": "simple",
        "nodes": [{"id": "start", "type": "noop"}, {"id": "emit", "type": "emit_event", "config": {"topic": "x"}}],
        "edges": [{"from": "start", "to": "emit"}],
    })
    outcome = execute_workflow_plan(spec, {"hello": "world"})
    assert outcome.status == "succeeded"
    assert [step.node_id for step in outcome.steps] == ["start", "emit"]


def test_execute_stops_for_approval():
    spec = WorkflowSpec.model_validate({
        "name": "command",
        "nodes": [{"id": "cmd", "type": "command_request", "config": {"template_id": "coding_harness"}}],
    })
    outcome = execute_workflow_plan(spec)
    assert outcome.status == "pending_approval"
    assert outcome.steps[0].requires_approval


def test_execute_approved_side_effect_records_queue_marker():
    spec = WorkflowSpec.model_validate({
        "name": "command",
        "nodes": [{"id": "cmd", "type": "command_request", "config": {"template_id": "coding_harness", "secret_token": "abc"}}],
    })
    outcome = execute_workflow_plan(spec, approved_nodes={"cmd"})
    assert outcome.status == "succeeded"
    assert outcome.steps[0].output["queued_side_effect"] is True
    assert outcome.steps[0].output["config"]["secret_token"] == "<redacted>"


def test_dependency_skips_after_pending_approval():
    spec = WorkflowSpec.model_validate({
        "name": "approval-chain",
        "nodes": [{"id": "gate", "type": "approval_gate"}, {"id": "after", "type": "noop"}],
        "edges": [{"from": "gate", "to": "after"}],
    })
    outcome = execute_workflow_plan(spec)
    assert outcome.status == "pending_approval"
    assert outcome.steps[1].status.value == "skipped"
