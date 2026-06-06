from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

from .dag import DAGValidationError, validate_dag
from .models import NodeType, WorkflowNode, WorkflowSpec

INTERNAL_HOSTS = {
    "api-gateway",
    "sync-engine",
    "module-service",
    "command-bus",
    "research-service",
    "automation-service",
    "localhost",
    "127.0.0.1",
}
FORBIDDEN_SCOPES = {
    "shell:raw",
    "filesystem:host-write",
    "network:scan",
    "privileged:container",
    "secrets:read",
}
SIDE_EFFECT_NODE_TYPES = {
    NodeType.HTTP_REQUEST,
    NodeType.MODULE_API,
    NodeType.COMMAND_REQUEST,
    NodeType.NOTIFICATION,
    NodeType.N8N_WEBHOOK,
    NodeType.ARTIFACT,
}
MANDATORY_APPROVAL_NODE_TYPES = {
    NodeType.COMMAND_REQUEST,
    NodeType.N8N_WEBHOOK,
}


@dataclass(frozen=True)
class NodeDecision:
    node_id: str
    allowed: bool
    requires_approval: bool
    denials: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_scopes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkflowDecision:
    allowed: bool
    requires_approval: bool
    denials: list[str]
    warnings: list[str]
    required_scopes: list[str]
    node_decisions: list[NodeDecision]


def evaluate_node_policy(node: WorkflowNode) -> NodeDecision:
    denials: list[str] = []
    warnings: list[str] = []
    required_scopes = sorted(set(node.scopes))
    requires_approval = node.requires_approval or node.type in MANDATORY_APPROVAL_NODE_TYPES

    forbidden = sorted(FORBIDDEN_SCOPES.intersection(required_scopes))
    if forbidden:
        denials.append(f"forbidden scopes requested: {', '.join(forbidden)}")

    if node.config.get("destructive") is True:
        requires_approval = True
        warnings.append("node declares destructive behavior")

    if node.type == NodeType.HTTP_REQUEST:
        method = str(node.config.get("method", "GET")).upper()
        url = str(node.config.get("url", ""))
        parsed = urlparse(url)
        if method not in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"}:
            denials.append(f"unsupported HTTP method: {method}")
        if not parsed.scheme or not parsed.netloc:
            denials.append("http_request nodes require an absolute url")
        else:
            host = parsed.hostname or ""
            external = host not in INTERNAL_HOSTS and not host.endswith(".internal")
            if external:
                requires_approval = True
                if node.config.get("external_allowed") is not True:
                    denials.append("external HTTP destinations require config.external_allowed=true")
            if method not in {"GET", "HEAD"}:
                requires_approval = True

    if node.type == NodeType.MODULE_API:
        path = str(node.config.get("path", ""))
        if not path.startswith("/api/"):
            denials.append("module_api nodes must target /api/* paths")
        method = str(node.config.get("method", "GET")).upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            denials.append(f"unsupported module_api method: {method}")
        if method != "GET":
            requires_approval = requires_approval or bool(node.config.get("approval_for_write", True))

    if node.type == NodeType.COMMAND_REQUEST:
        template_id = node.config.get("template_id")
        if not template_id:
            denials.append("command_request nodes require a command template_id")
        requires_approval = True

    if node.type == NodeType.NOTIFICATION:
        if not node.config.get("topic") and not node.config.get("channel"):
            denials.append("notification nodes require topic or channel")

    if node.type == NodeType.N8N_WEBHOOK:
        if not node.config.get("webhook_path") and not node.config.get("url"):
            denials.append("n8n_webhook nodes require webhook_path or url")
        requires_approval = True

    if node.type == NodeType.APPROVAL_GATE:
        requires_approval = True

    return NodeDecision(
        node_id=node.id,
        allowed=not denials,
        requires_approval=requires_approval,
        denials=denials,
        warnings=warnings,
        required_scopes=required_scopes,
    )


def evaluate_workflow_policy(spec: WorkflowSpec) -> WorkflowDecision:
    denials: list[str] = []
    warnings: list[str] = []
    try:
        validate_dag(spec)
    except DAGValidationError as exc:
        denials.append(str(exc))

    if len(spec.nodes) > 64:
        denials.append("workflow exceeds 64 nodes")
    if spec.max_concurrency > 4:
        warnings.append("high max_concurrency should be used only for idempotent workflows")

    node_decisions = [evaluate_node_policy(node) for node in spec.nodes]
    for decision in node_decisions:
        denials.extend(f"{decision.node_id}: {message}" for message in decision.denials)
        warnings.extend(f"{decision.node_id}: {message}" for message in decision.warnings)

    required_scopes = sorted({scope for d in node_decisions for scope in d.required_scopes})
    requires_approval = spec.requires_approval or any(d.requires_approval for d in node_decisions)
    return WorkflowDecision(
        allowed=not denials,
        requires_approval=requires_approval,
        denials=denials,
        warnings=warnings,
        required_scopes=required_scopes,
        node_decisions=node_decisions,
    )
