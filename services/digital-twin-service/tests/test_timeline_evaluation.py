from datetime import datetime, timezone

from app.evaluation import evaluate_golden_cases
from app.timeline import aggregate_timeline, infer_state_from_events, normalize_event


def test_normalize_event_is_deterministic_for_same_inputs():
    when = datetime(2026, 6, 6, tzinfo=timezone.utc)
    a = normalize_event("study.session.completed", {"importance": 0.9}, when, "test")
    b = normalize_event("study.session.completed", {"importance": 0.9}, when, "test")
    assert a["event_uid"] == b["event_uid"]
    assert a["domains"] == ["learning"]


def test_aggregate_and_infer_state():
    events = [
        normalize_event("study.session.completed", {"importance": 0.8}),
        normalize_event("research.document.ingested", {"importance": 0.5}),
        normalize_event("automation.run.completed", {"importance": 0.6}),
    ]
    summary = aggregate_timeline(events)
    assert summary["event_count"] == 3
    state = infer_state_from_events(events)
    assert state["learning_momentum"] > 0
    assert state["ops_pressure"] > 0


def test_golden_evaluation_score_is_perfect():
    result = evaluate_golden_cases()
    assert result["score"] == 1.0
    assert result["passed"] == result["total"]


def test_aggregate_empty_timeline():
    summary = aggregate_timeline([])
    assert summary['event_count'] == 0
    assert summary['importance_avg'] == 0.0
    state = infer_state_from_events([])
    assert state['confidence'] == 0.1
