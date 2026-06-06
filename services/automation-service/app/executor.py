from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .dag import validate_dag
from .models import NodeType, StepStatus, WorkflowSpec
from .policy import evaluate_node_policy


@dataclass(frozen=True)
class StepOutcome:
    node_id: str
    status: StepStatus
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    requires_approval: bool = False


@dataclass(frozen=True)
class RunOutcome:
    status: str
    steps: list[StepOutcome]
    output: dict[str, Any]


def execute_workflow_plan(spec: WorkflowSpec, payload: dict[str, Any] | None = None, *, approved_nodes: set[str] | None = None) -> RunOutcome:
    payload = payload or {}
    approved_nodes = approved_nodes or set()
    plan = validate_dag(spec)
    context: dict[str, Any] = {"input": payload, "steps": {}}
    outcomes: list[StepOutcome] = []
    pending = False

    for node_id in plan.order:
        node = spec.node_by_id(node_id)
        predecessors = plan.reverse_adjacency.get(node_id, [])
        if any(context["steps"].get(parent, {}).get("status") not in {StepStatus.SUCCEEDED.value} for parent in predecessors):
            outcome = StepOutcome(node_id=node_id, status=StepStatus.SKIPPED, error="upstream dependency not satisfied")
            outcomes.append(outcome)
            context["steps"][node_id] = outcome_to_dict(outcome)
            continue

        decision = evaluate_node_policy(node)
        if not decision.allowed:
            outcome = StepOutcome(node_id=node_id, status=StepStatus.FAILED, error="; ".join(decision.denials))
            outcomes.append(outcome)
            context["steps"][node_id] = outcome_to_dict(outcome)
            return RunOutcome(status="failed", steps=outcomes, output=context)

        if decision.requires_approval and node_id not in approved_nodes:
            outcome = StepOutcome(node_id=node_id, status=StepStatus.PENDING_APPROVAL, requires_approval=True, output={"reason": "approval required"})
            outcomes.append(outcome)
            context["steps"][node_id] = outcome_to_dict(outcome)
            pending = True
            continue

        outcome = execute_node(node.type, node.config, context)
        outcomes.append(StepOutcome(node_id=node_id, **outcome))
        context["steps"][node_id] = {"status": outcome["status"].value, "output": outcome.get("output", {})}

    if any(step.status == StepStatus.FAILED for step in outcomes):
        status = "failed"
    elif pending or any(step.status == StepStatus.PENDING_APPROVAL for step in outcomes):
        status = "pending_approval"
    else:
        status = "succeeded"
    return RunOutcome(status=status, steps=outcomes, output=context)


def execute_node(node_type: NodeType, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    if node_type == NodeType.NOOP:
        return {"status": StepStatus.SUCCEEDED, "output": {"ok": True}}
    if node_type == NodeType.TRANSFORM:
        return {"status": StepStatus.SUCCEEDED, "output": {"value": config.get("output", {}), "input": context.get("input", {})}}
    if node_type == NodeType.EMIT_EVENT:
        return {"status": StepStatus.SUCCEEDED, "output": {"topic": config.get("topic"), "payload": config.get("payload", {})}}
    if node_type == NodeType.ARTIFACT:
        return {"status": StepStatus.SUCCEEDED, "output": {"artifact": config.get("artifact", {}), "mode": "record_only"}}
    if node_type in {NodeType.HTTP_REQUEST, NodeType.MODULE_API, NodeType.COMMAND_REQUEST, NodeType.NOTIFICATION, NodeType.N8N_WEBHOOK}:
        return {"status": StepStatus.SUCCEEDED, "output": {"queued_side_effect": True, "type": node_type.value, "config": safe_config(config)}}
    if node_type == NodeType.APPROVAL_GATE:
        return {"status": StepStatus.SUCCEEDED, "output": {"approved": True}}
    return {"status": StepStatus.FAILED, "error": f"unsupported node type {node_type}"}


def safe_config(config: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(config)
    for key in list(redacted):
        if any(token in key.lower() for token in ("secret", "token", "password", "key")):
            redacted[key] = "<redacted>"
    return redacted


def outcome_to_dict(outcome: StepOutcome) -> dict[str, Any]:
    return {
        "node_id": outcome.node_id,
        "status": outcome.status.value,
        "output": outcome.output,
        "error": outcome.error,
        "requires_approval": outcome.requires_approval,
    }
