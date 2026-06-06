from datetime import datetime, timezone

import pytest

from app.dag import DAGValidationError, validate_dag
from app.executor import execute_node, execute_workflow_plan
from app.models import NodeType, StepStatus, WorkflowNode, WorkflowSpec
from app.n8n_bridge import verify_payload_signature
from app.notifications import build_notification
from app.policy import evaluate_node_policy, evaluate_workflow_policy
from app.scheduler import is_interval_due, next_interval_due, normalize_utc, stable_jitter_seconds


def test_self_edge_rejected_and_duplicate_edge_ignored():
    with pytest.raises(DAGValidationError, match="self edges"):
        validate_dag(WorkflowSpec.model_validate({"name": "self", "nodes": [{"id": "a"}], "edges": [{"from": "a", "to": "a"}]}))
    spec = WorkflowSpec.model_validate({
        "name": "dupe-edge",
        "nodes": [{"id": "a"}, {"id": "b"}],
        "edges": [{"from": "a", "to": "b"}, {"from": "a", "to": "b"}],
    })
    plan = validate_dag(spec)
    assert plan.adjacency["a"] == ["b"]


def test_policy_destructive_module_command_notification_and_n8n_branches():
    destructive = evaluate_node_policy(WorkflowNode(id="d", type="noop", config={"destructive": True}))
    assert destructive.requires_approval
    assert destructive.warnings

    bad_module = evaluate_node_policy(WorkflowNode(id="m", type="module_api", config={"path": "not-api", "method": "TRACE"}))
    assert not bad_module.allowed
    assert len(bad_module.denials) == 2

    write_module = evaluate_node_policy(WorkflowNode(id="mw", type="module_api", config={"path": "/api/study/items", "method": "POST"}))
    assert write_module.allowed and write_module.requires_approval

    no_template = evaluate_node_policy(WorkflowNode(id="c", type="command_request"))
    assert not no_template.allowed
    assert no_template.requires_approval

    bad_notification = evaluate_node_policy(WorkflowNode(id="n", type="notification"))
    assert not bad_notification.allowed

    bad_n8n = evaluate_node_policy(WorkflowNode(id="n8n", type="n8n_webhook"))
    assert not bad_n8n.allowed
    assert bad_n8n.requires_approval

    gate = evaluate_node_policy(WorkflowNode(id="g", type="approval_gate"))
    assert gate.allowed and gate.requires_approval


def test_workflow_policy_invalid_dag_and_concurrency_warning():
    spec = WorkflowSpec.model_validate({
        "name": "cyclic",
        "max_concurrency": 8,
        "nodes": [{"id": "a"}, {"id": "b"}],
        "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}],
    })
    decision = evaluate_workflow_policy(spec)
    assert not decision.allowed
    assert any(("cycle" in d or "root" in d) for d in decision.denials)
    assert decision.warnings


def test_executor_failure_artifact_gate_and_unsupported_paths():
    bad = WorkflowSpec.model_validate({"name": "bad", "nodes": [{"id": "n", "type": "notification"}]})
    failed = execute_workflow_plan(bad)
    assert failed.status == "failed"
    assert failed.steps[0].status == StepStatus.FAILED

    artifact = execute_node(NodeType.ARTIFACT, {"artifact": {"name": "x"}}, {})
    assert artifact["status"] == StepStatus.SUCCEEDED
    assert artifact["output"]["mode"] == "record_only"

    gate = execute_node(NodeType.APPROVAL_GATE, {}, {})
    assert gate["output"]["approved"] is True

    unsupported = execute_node("unknown", {}, {})  # type: ignore[arg-type]
    assert unsupported["status"] == StepStatus.FAILED


def test_scheduler_naive_none_and_zero_jitter_branches():
    naive = datetime(2026, 1, 1)
    assert normalize_utc(naive).tzinfo is timezone.utc
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert next_interval_due(None, 60, now=now) == now
    assert is_interval_due(None, 60, now=now)
    assert stable_jitter_seconds("x", 0) == 0


def test_n8n_bad_timestamp_and_notification_priority_branch():
    assert not verify_payload_signature({"a": 1}, "t=abc,v1=x", "secret", now=100)
    high = build_notification("topic", "title", "message", priority="high")
    assert high["priority"] == "high"


def test_remaining_policy_and_executor_branches():
    bad_http = evaluate_node_policy(WorkflowNode(id="h", type="http_request", config={"url": "not-a-url", "method": "TRACE"}))
    assert not bad_http.allowed
    assert any("unsupported HTTP" in d for d in bad_http.denials)
    assert any("absolute url" in d for d in bad_http.denials)

    no_approval_write = evaluate_node_policy(WorkflowNode(id="m", type="module_api", config={"path": "/api/study/items", "method": "POST", "approval_for_write": False}))
    assert no_approval_write.allowed
    assert not no_approval_write.requires_approval

    n8n_ok = evaluate_node_policy(WorkflowNode(id="n8", type="n8n_webhook", config={"webhook_path": "/webhook/x"}))
    assert n8n_ok.allowed and n8n_ok.requires_approval

    transformed = execute_node(NodeType.TRANSFORM, {"output": {"x": 1}}, {"input": {"y": 2}})
    assert transformed["output"]["value"] == {"x": 1}

    failed_status = execute_workflow_plan(WorkflowSpec.model_validate({"name": "bad", "nodes": [{"id": "h", "type": "http_request", "config": {"url": "bad"}}]}))
    assert failed_status.status == "failed"
