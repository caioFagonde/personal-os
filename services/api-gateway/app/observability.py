from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from statistics import mean
from threading import Lock


@dataclass(frozen=True)
class HealthSnapshot:
    service: str
    ok: bool
    latency_ms: float
    checked_at: float


class RedMetrics:
    """Small dependency-free RED metric collector for local/offline deployments."""

    def __init__(self, window_size: int = 256) -> None:
        self.window_size = window_size
        self._lock = Lock()
        self._requests: dict[str, int] = defaultdict(int)
        self._errors: dict[str, int] = defaultdict(int)
        self._durations: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=window_size))

    def observe(self, route: str, status_code: int, duration_ms: float) -> None:
        if duration_ms < 0:
            raise ValueError("duration_ms cannot be negative")
        route_key = route or "unknown"
        with self._lock:
            self._requests[route_key] += 1
            if status_code >= 500:
                self._errors[route_key] += 1
            self._durations[route_key].append(duration_ms)

    def snapshot(self) -> dict[str, dict[str, float | int]]:
        with self._lock:
            routes = sorted(set(self._requests) | set(self._durations) | set(self._errors))
            return {
                route: {
                    "requests": self._requests.get(route, 0),
                    "errors": self._errors.get(route, 0),
                    "avg_duration_ms": round(mean(self._durations[route]), 3) if self._durations.get(route) else 0.0,
                    "max_duration_ms": round(max(self._durations[route]), 3) if self._durations.get(route) else 0.0,
                }
                for route in routes
            }

    def prometheus(self, *, service_name: str) -> str:
        lines = [
            "# HELP personal_os_requests_total Total HTTP requests observed by the in-process RED collector.",
            "# TYPE personal_os_requests_total counter",
        ]
        snap = self.snapshot()
        for route, values in snap.items():
            labels = f'service="{service_name}",route="{route}"'
            lines.append(f"personal_os_requests_total{{{labels}}} {values['requests']}")
        lines.extend([
            "# HELP personal_os_errors_total HTTP 5xx responses observed by the in-process RED collector.",
            "# TYPE personal_os_errors_total counter",
        ])
        for route, values in snap.items():
            labels = f'service="{service_name}",route="{route}"'
            lines.append(f"personal_os_errors_total{{{labels}}} {values['errors']}")
        lines.extend([
            "# HELP personal_os_request_duration_ms Average request duration in milliseconds.",
            "# TYPE personal_os_request_duration_ms gauge",
        ])
        for route, values in snap.items():
            labels = f'service="{service_name}",route="{route}"'
            lines.append(f"personal_os_request_duration_ms{{{labels}}} {values['avg_duration_ms']}")
        return "\n".join(lines) + "\n"


def aggregate_health(snapshots: list[HealthSnapshot]) -> dict[str, object]:
    if not snapshots:
        return {"status": "unknown", "services": {}, "degraded": []}
    services = {s.service: {"ok": s.ok, "latency_ms": round(s.latency_ms, 2), "checked_at": s.checked_at} for s in snapshots}
    degraded = sorted(s.service for s in snapshots if not s.ok)
    return {"status": "ok" if not degraded else "degraded", "services": services, "degraded": degraded}


def now_snapshot(service: str, ok: bool, started_at: float) -> HealthSnapshot:
    current = time.time()
    return HealthSnapshot(service=service, ok=ok, latency_ms=(current - started_at) * 1000.0, checked_at=current)
