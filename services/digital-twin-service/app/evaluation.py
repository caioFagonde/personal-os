from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .recommender import generate_recommendations

@dataclass(frozen=True)
class EvaluationCase:
    name: str
    state: dict[str, Any]
    goals: list[dict[str, Any]]
    expected_domains: set[str]
    forbidden_action_types: set[str] | None = None

GOLDEN_CASES = [
    EvaluationCase(
        name="low_energy_prioritizes_recovery",
        state={"cognitive_energy": 0.2, "sleep_quality": 0.35, "focus_distribution": {"learning": 0.4}, "learning_momentum": 0.6},
        goals=[],
        expected_domains={"health"},
    ),
    EvaluationCase(
        name="learning_goal_triggers_study",
        state={"cognitive_energy": 0.8, "sleep_quality": 0.8, "learning_momentum": 0.1, "focus_distribution": {}},
        goals=[{"id": "g1", "title": "Master variational inference", "domain": "learning", "priority": 80, "progress": 0.2}],
        expected_domains={"learning"},
    ),
    EvaluationCase(
        name="ops_pressure_requires_gate",
        state={"ops_pressure": 0.9, "recovery_pressure": 0.1, "focus_distribution": {"automation": 0.8}, "cognitive_energy": 0.7},
        goals=[],
        expected_domains={"operations"},
    ),
]


def evaluate_case(case: EvaluationCase) -> dict[str, Any]:
    recs = generate_recommendations(case.state, case.goals, [])
    domains = {r["domain"] for r in recs}
    actions = {r["action_type"] for r in recs}
    missing = case.expected_domains - domains
    forbidden = (case.forbidden_action_types or set()) & actions
    passed = not missing and not forbidden
    return {
        "name": case.name,
        "passed": passed,
        "missing_domains": sorted(missing),
        "forbidden_actions": sorted(forbidden),
        "recommendations": recs,
    }


def evaluate_golden_cases() -> dict[str, Any]:
    results = [evaluate_case(case) for case in GOLDEN_CASES]
    passed = sum(1 for r in results if r["passed"])
    return {
        "passed": passed,
        "total": len(results),
        "score": round(passed / len(results), 4),
        "results": results,
    }
