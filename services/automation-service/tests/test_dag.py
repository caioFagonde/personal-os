import pytest

from app.dag import DAGValidationError, validate_dag
from app.models import WorkflowSpec


def spec(**overrides):
    data = {
        "name": "test",
        "nodes": [{"id": "a", "type": "noop"}, {"id": "b", "type": "noop"}, {"id": "c", "type": "noop"}],
        "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}],
    }
    data.update(overrides)
    return WorkflowSpec.model_validate(data)


def test_topological_order_roots_and_leaves():
    plan = validate_dag(spec())
    assert plan.order == ["a", "b", "c"]
    assert plan.roots == ["a"]
    assert plan.leaves == ["c"]


def test_unknown_edge_rejected():
    with pytest.raises(DAGValidationError, match="unknown node"):
        validate_dag(spec(edges=[{"from": "a", "to": "missing"}]))


def test_cycle_rejected():
    with pytest.raises(DAGValidationError, match="cycle"):
        validate_dag(spec(edges=[{"from": "a", "to": "b"}, {"from": "b", "to": "a"}]))


def test_duplicate_node_rejected():
    with pytest.raises(DAGValidationError, match="duplicate"):
        validate_dag(WorkflowSpec.model_validate({"name": "dup", "nodes": [{"id": "x"}, {"id": "x"}]}))
