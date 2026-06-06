from app.models import WorkflowNode, WorkflowSpec
from app.policy import evaluate_node_policy, evaluate_workflow_policy


def test_forbidden_scope_denies_node():
    decision = evaluate_node_policy(WorkflowNode(id="danger", type="command_request", scopes=["shell:raw"], config={"template_id": "safe"}))
    assert not decision.allowed
    assert "forbidden scopes" in decision.denials[0]


def test_external_http_requires_explicit_allow_and_approval():
    decision = evaluate_node_policy(WorkflowNode(id="http", type="http_request", config={"url": "https://example.com/x", "method": "POST"}))
    assert not decision.allowed
    assert decision.requires_approval


def test_external_http_can_be_allowed_but_still_requires_approval():
    decision = evaluate_node_policy(WorkflowNode(id="http", type="http_request", config={"url": "https://example.com/x", "method": "GET", "external_allowed": True}))
    assert decision.allowed
    assert decision.requires_approval


def test_internal_get_is_allowed_without_approval():
    decision = evaluate_node_policy(WorkflowNode(id="http", type="http_request", config={"url": "http://module-service:8083/api/study/items", "method": "GET"}))
    assert decision.allowed
    assert not decision.requires_approval


def test_workflow_policy_accumulates_scopes_and_approval():
    spec = WorkflowSpec.model_validate({
        "name": "notify",
        "nodes": [
            {"id": "a", "type": "noop"},
            {"id": "n", "type": "notification", "scopes": ["notifications:send"], "config": {"topic": "x"}},
        ],
        "edges": [{"from": "a", "to": "n"}],
    })
    decision = evaluate_workflow_policy(spec)
    assert decision.allowed
    assert "notifications:send" in decision.required_scopes
