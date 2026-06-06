from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from .models import WorkflowSpec


class DAGValidationError(ValueError):
    pass


@dataclass(frozen=True)
class DAGPlan:
    order: list[str]
    roots: list[str]
    leaves: list[str]
    adjacency: dict[str, list[str]]
    reverse_adjacency: dict[str, list[str]]


def validate_dag(spec: WorkflowSpec) -> DAGPlan:
    node_ids = [node.id for node in spec.nodes]
    if len(node_ids) != len(set(node_ids)):
        raise DAGValidationError("workflow contains duplicate node ids")

    known = set(node_ids)
    adjacency: dict[str, list[str]] = defaultdict(list)
    reverse: dict[str, list[str]] = defaultdict(list)
    in_degree = {node_id: 0 for node_id in node_ids}

    for edge in spec.edges:
        source = edge.from_node
        target = edge.to_node
        if source not in known or target not in known:
            raise DAGValidationError(f"edge references unknown node: {source}->{target}")
        if source == target:
            raise DAGValidationError(f"self edges are not allowed: {source}")
        if target not in adjacency[source]:
            adjacency[source].append(target)
            reverse[target].append(source)
            in_degree[target] += 1

    roots = sorted(node_id for node_id, degree in in_degree.items() if degree == 0)
    if not roots:
        raise DAGValidationError("workflow must have at least one root node")

    queue = deque(roots)
    order: list[str] = []
    while queue:
        current = queue.popleft()
        order.append(current)
        for child in sorted(adjacency.get(current, [])):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    if len(order) != len(node_ids):
        unresolved = sorted(set(node_ids) - set(order))
        raise DAGValidationError(f"workflow contains a cycle involving: {', '.join(unresolved)}")

    leaves = sorted(node_id for node_id in node_ids if not adjacency.get(node_id))
    return DAGPlan(
        order=order,
        roots=roots,
        leaves=leaves,
        adjacency={k: sorted(v) for k, v in adjacency.items()},
        reverse_adjacency={k: sorted(v) for k, v in reverse.items()},
    )
