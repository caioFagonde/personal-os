from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Routine:
    id: str
    cron: str
    purpose: str
    service: str
    priority: str = "normal"


ROUTINES = [
    Routine("study.due_reviews", "*/20 * * * *", "queue due flashcard and reading reviews", "study-companion", "high"),
    Routine("study.retention_rebalance", "0 5 * * *", "rebalance intervals using recall outcomes and fatigue signals", "study-companion"),
    Routine("study.daily_plan", "30 6 * * 1-6", "generate daily reading/review plan", "study-companion"),
    Routine("analog.ocr_backlog", "*/10 * * * *", "process unparsed camera/audio/file captures", "study-companion", "high"),
    Routine("analog.deep_lookup", "*/15 * * * *", "expand object/passage lookup cards into related research candidates", "study-companion"),
    Routine("zettel.backlinks", "*/30 * * * *", "refresh backlinks and orphan-note report", "module-service"),
    Routine("ar.spatial_recall", "*/5 * * * *", "match current pose/location to spatial notes for popup recall", "module-service"),
    Routine("tasks.followups", "*/30 * * * *", "remind about delegated tasks without acknowledgement", "capture-service", "high"),
    Routine("sync.health", "*/5 * * * *", "verify device sync lag and conflict count", "sync-engine", "high"),
    Routine("backup.encrypted", "0 3 * * *", "run encrypted database/object-store backup", "ops", "high"),
]


def recommended_routines(include_experimental: bool = False) -> list[dict[str, str]]:
    rows = [r.__dict__ for r in ROUTINES]
    if include_experimental:
        rows.append({"id": "vision.live_video_sampling", "cron": "*/1 * * * *", "purpose": "sample live video frames when explicitly enabled", "service": "study-companion", "priority": "low"})
    return rows


def cron_for(routine_id: str) -> str | None:
    for routine in ROUTINES:
        if routine.id == routine_id:
            return routine.cron
    return None
