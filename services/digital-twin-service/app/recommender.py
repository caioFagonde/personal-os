from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

@dataclass(frozen=True)
class Recommendation:
    id: str
    title: str
    rationale: str
    domain: str
    priority: int
    confidence: float
    action_type: str
    action: dict[str, Any]
    requires_approval: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "rationale": self.rationale,
            "domain": self.domain,
            "priority": self.priority,
            "confidence": round(self.confidence, 4),
            "action_type": self.action_type,
            "action": self.action,
            "requires_approval": self.requires_approval,
        }


def _rid(title: str, domain: str, action: dict[str, Any]) -> str:
    return sha256(f"{title}|{domain}|{action}".encode()).hexdigest()[:16]


def _rec(title: str, rationale: str, domain: str, priority: int, confidence: float, action_type: str, action: dict[str, Any], requires_approval: bool = False) -> Recommendation:
    return Recommendation(_rid(title, domain, action), title, rationale, domain, priority, min(1.0, max(0.0, confidence)), action_type, action, requires_approval)


def generate_recommendations(state: dict[str, Any], goals: list[dict[str, Any]] | None = None, recent_events: list[dict[str, Any]] | None = None, preferences: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    goals = goals or []
    recent_events = recent_events or []
    preferences = preferences or {}
    recs: list[Recommendation] = []
    focus_distribution = state.get("focus_distribution") or {}
    learning = float(state.get("learning_momentum", 0.0))
    recovery = float(state.get("recovery_pressure", 0.0))
    ops = float(state.get("ops_pressure", 0.0))
    cognitive_energy = float(state.get("cognitive_energy", preferences.get("default_cognitive_energy", 0.6)))
    sleep_quality = float(state.get("sleep_quality", 0.7))

    if cognitive_energy < 0.35 or sleep_quality < 0.45:
        recs.append(_rec(
            "Run a recovery-first block",
            "The current state indicates low cognitive energy or poor sleep. A bounded recovery block protects tomorrow's throughput.",
            "health",
            95,
            0.88,
            "schedule_block",
            {"duration_minutes": 30, "kind": "recovery", "notification": True},
        ))

    if learning < 0.35 and any(g.get("domain") in {"study", "learning", "research"} or g.get("kind") == "learning" for g in goals):
        recs.append(_rec(
            "Open a 45-minute deep study sprint",
            "Learning goals exist but the recent timeline has low learning momentum.",
            "learning",
            88,
            0.82,
            "start_module_session",
            {"module": "study", "duration_minutes": 45, "mode": "deep_work"},
        ))

    overdue = [g for g in goals if g.get("status") not in {"done", "archived"} and float(g.get("progress", 0.0)) < 0.35 and int(g.get("priority", 50)) >= 70]
    if overdue:
        target = sorted(overdue, key=lambda g: int(g.get("priority", 50)), reverse=True)[0]
        recs.append(_rec(
            f"Advance goal: {target.get('title', 'priority goal')}",
            "A high-priority goal has low recorded progress. The system should convert it into a concrete next action.",
            str(target.get("domain", "planning")),
            92,
            0.86,
            "create_next_action",
            {"goal_id": target.get("id"), "title": target.get("title"), "duration_minutes": 25},
        ))

    if ops > 0.65 and recovery < 0.2:
        recs.append(_rec(
            "Insert an ops cooldown checkpoint",
            "Automation/command activity is high. A checkpoint reduces runaway operational complexity.",
            "operations",
            80,
            0.74,
            "approval_gate",
            {"reason": "high operational pressure", "review_minutes": 10},
            requires_approval=True,
        ))

    if focus_distribution.get("mindfulness", 0.0) < 0.08 and len(recent_events) >= 5:
        recs.append(_rec(
            "Capture a two-minute reflection",
            "Recent activity exists but reflection/mindfulness signals are sparse. Short reflection improves digital-twin state quality.",
            "mindfulness",
            64,
            0.68,
            "open_module",
            {"module": "mindfulness", "prompt": "What did today teach me?"},
        ))

    if not recs:
        recs.append(_rec(
            "Maintain current trajectory",
            "No high-pressure imbalance was detected. Continue with the active plan and collect more state observations.",
            "planning",
            40,
            0.55,
            "observe",
            {"collect": ["study", "health", "automation"]},
        ))

    deduped: dict[str, Recommendation] = {}
    for rec in recs:
        current = deduped.get(rec.id)
        if current is None or rec.priority > current.priority:
            deduped[rec.id] = rec
    return [r.as_dict() for r in sorted(deduped.values(), key=lambda r: (-r.priority, -r.confidence, r.title))]
