from app.recommender import generate_recommendations


def test_low_energy_recommends_recovery_first():
    recs = generate_recommendations({"cognitive_energy": 0.2, "sleep_quality": 0.9, "focus_distribution": {}})
    assert recs[0]["domain"] == "health"
    assert recs[0]["priority"] >= 90


def test_learning_goal_generates_study_action():
    recs = generate_recommendations(
        {"learning_momentum": 0.1, "cognitive_energy": 0.8, "focus_distribution": {}},
        [{"id": "g1", "title": "Learn pgRouting", "domain": "learning", "priority": 80, "progress": 0.5}],
    )
    assert any(r["action"].get("module") == "study" for r in recs)


def test_overdue_goal_generates_next_action():
    recs = generate_recommendations(
        {"learning_momentum": 0.8, "cognitive_energy": 0.8, "focus_distribution": {"mindfulness": 0.2}},
        [{"id": "g2", "title": "Ship desktop shell", "domain": "work", "priority": 95, "progress": 0.1}],
    )
    assert recs[0]["action_type"] == "create_next_action"
    assert recs[0]["action"]["goal_id"] == "g2"


def test_ops_pressure_requires_approval_gate():
    recs = generate_recommendations({"ops_pressure": 0.9, "recovery_pressure": 0.0, "cognitive_energy": 0.7, "focus_distribution": {"automation": 1.0}})
    gate = [r for r in recs if r["action_type"] == "approval_gate"]
    assert gate and gate[0]["requires_approval"]


def test_default_observe_when_no_pressure():
    recs = generate_recommendations({"learning_momentum": 0.8, "cognitive_energy": 0.8, "focus_distribution": {"mindfulness": 0.2}})
    assert recs[0]["action_type"] == "observe"


def test_mindfulness_recommendation_when_recent_events_are_reflection_sparse():
    recs = generate_recommendations(
        {'learning_momentum': 0.8, 'cognitive_energy': 0.8, 'focus_distribution': {'learning': 1.0}},
        [],
        [{'event_type': f'e{i}'} for i in range(5)],
    )
    assert any(r['domain'] == 'mindfulness' for r in recs)
