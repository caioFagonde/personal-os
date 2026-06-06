from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


class LearningAtomKind(str, Enum):
    fact = "fact"
    concept = "concept"
    procedure = "procedure"
    passage = "passage"
    object = "object"


@dataclass(frozen=True)
class ReviewState:
    interval_days: int = 1
    ease_factor: float = 2.5
    repetitions: int = 0
    stability: float = 1.0
    difficulty: float = 5.0


@dataclass(frozen=True)
class ReviewResult:
    interval_days: int
    ease_factor: float
    repetitions: int
    stability: float
    difficulty: float
    due_at: datetime
    retention_probability: float
    rationale: str


def sm2_plus(quality: int, state: ReviewState | None = None, now: datetime | None = None) -> ReviewResult:
    """SM-2 compatible scheduler with stability/difficulty fields for later FSRS migration."""
    if quality < 0 or quality > 5:
        raise ValueError("quality must be between 0 and 5")
    state = state or ReviewState()
    now = now or datetime.now(timezone.utc)
    ef = max(1.3, state.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    difficulty = min(10.0, max(1.0, state.difficulty + (3 - quality) * 0.45))
    if quality < 3:
        repetitions = 0
        interval = 1
        stability = max(0.5, state.stability * 0.55)
        rationale = "reset after failed recall"
    else:
        repetitions = state.repetitions + 1
        if repetitions == 1:
            interval = 1
        elif repetitions == 2:
            interval = 3 if quality == 3 else 6
        else:
            interval = max(1, round(state.interval_days * ef * (1.0 + (quality - 3) * 0.12)))
        stability = max(1.0, state.stability * (1.0 + ef / 3.0 + (quality - 3) * 0.15))
        rationale = "extended interval after successful recall"
    due_at = now + timedelta(days=interval)
    retention = retention_probability(days_elapsed=interval, stability=stability)
    return ReviewResult(interval, round(ef, 3), repetitions, round(stability, 3), round(difficulty, 3), due_at, retention, rationale)


def retention_probability(days_elapsed: float, stability: float) -> float:
    if stability <= 0:
        return 0.0
    return round(math.exp(-max(days_elapsed, 0.0) / stability), 4)


def desirable_difficulty(recall_quality: int, confidence: float, time_seconds: int | None = None) -> str:
    if recall_quality <= 2 or confidence < 0.35:
        return "too_hard"
    if recall_quality >= 5 and confidence > 0.85 and (time_seconds is None or time_seconds < 20):
        return "too_easy"
    return "productive"


def interleave_plan(tags: list[str], due_count: int, new_count: int) -> list[str]:
    tags = [t for t in tags if t]
    plan = []
    for i in range(max(due_count, new_count, 1)):
        if i < due_count:
            plan.append("review_due")
        if tags:
            plan.append(f"crosslink:{tags[i % len(tags)]}")
        if i < new_count:
            plan.append("encode_new")
    return plan[: max(1, due_count + new_count + min(len(tags), 3))]


def reminder_schedule(created_at: datetime, urgency: str = "normal") -> list[datetime]:
    multipliers = {
        "low": [2, 7, 21],
        "normal": [1, 3, 7, 21],
        "high": [0, 1, 3, 7, 14],
    }.get(urgency, [1, 3, 7, 21])
    return [created_at + timedelta(days=d) for d in multipliers]
