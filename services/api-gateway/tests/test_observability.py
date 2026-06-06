from app.observability import HealthSnapshot, RedMetrics, aggregate_health


def test_red_metrics_records_requests_errors_and_durations():
    metrics = RedMetrics(window_size=2)
    metrics.observe("/health", 200, 10.0)
    metrics.observe("/health", 503, 30.0)
    metrics.observe("/api/modules", 200, 5.0)
    snap = metrics.snapshot()
    assert snap["/health"]["requests"] == 2
    assert snap["/health"]["errors"] == 1
    assert snap["/health"]["avg_duration_ms"] == 20.0
    prometheus = metrics.prometheus(service_name="api-gateway")
    assert "personal_os_requests_total" in prometheus
    assert 'route="/api/modules"' in prometheus


def test_red_metrics_rejects_negative_duration():
    metrics = RedMetrics()
    try:
        metrics.observe("/bad", 200, -1)
    except ValueError as exc:
        assert "duration" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("negative duration should fail")


def test_aggregate_health_marks_degraded_services():
    status = aggregate_health([
        HealthSnapshot("api", True, 1.0, 100.0),
        HealthSnapshot("sync", False, 80.0, 100.0),
    ])
    assert status["status"] == "degraded"
    assert status["degraded"] == ["sync"]
    assert status["services"]["api"]["ok"] is True


def test_aggregate_health_unknown_without_snapshots():
    assert aggregate_health([])["status"] == "unknown"
