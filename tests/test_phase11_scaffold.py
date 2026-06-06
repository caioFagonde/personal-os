from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_phase11_pages_and_routes_exist():
    pages = ROOT / "apps/web/src/pages"
    for name in ["ConnectorWorkerPage.vue", "ConflictResolutionPage.vue", "OfflineQueuePage.vue"]:
        assert (pages / name).exists(), name
    routes = (ROOT / "apps/web/src/router/routes.ts").read_text()
    for route in ["/connector-worker", "/conflicts", "/offline-queue"]:
        assert route in routes


def test_phase11_migration_and_worker_exist():
    assert (ROOT / "infra/postgres/migrations/010_phase_11_connector_worker_ui.sql").exists()
    worker = (ROOT / "services/connector-service/app/worker.py").read_text()
    assert "FOR UPDATE SKIP LOCKED" in worker
    assert "send_gmail" in worker
    assert "send_microsoft_mail" in worker
    assert "upload_backup" in worker


def test_compose_exposes_connector_worker_env():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    env = compose["services"]["connector-service"]["environment"]
    assert "CONNECTOR_WORKER_ENABLED" in env
    assert "CONNECTOR_WORKER_EXECUTE" in env


def test_bootstrap_runs_interactive_handoff():
    bootstrap = (ROOT / "scripts/bootstrap.sh").read_text()
    assert "auto-authorize.sh" in bootstrap
    assert "MOBILE_AUTO_DEPLOY" in bootstrap
