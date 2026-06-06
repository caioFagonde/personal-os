from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_phase9_services_exist():
    assert (ROOT / 'services/capture-service/app/parser.py').exists()
    assert (ROOT / 'services/capture-service/app/delegation.py').exists()
    assert (ROOT / 'services/study-companion-service/app/analog.py').exists()
    assert (ROOT / 'services/study-companion-service/app/retention.py').exists()


def test_phase9_migration_contains_core_tables():
    sql = (ROOT / 'infra/postgres/migrations/008_phase_9_capture_tasks_study_companion.sql').read_text()
    for table in ['tasks', 'capture_items', 'message_outbox', 'analog_captures', 'learning_atoms', 'lookup_cards']:
        assert f'CREATE TABLE IF NOT EXISTS {table}' in sql


def test_phase9_compose_services_and_gateway_env():
    compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
    services = compose['services']
    assert 'capture-service' in services
    assert 'study-companion-service' in services
    env = services['api-gateway']['environment']
    assert env['CAPTURE_SERVICE_URL'] == 'http://capture-service:8087'
    assert env['STUDY_COMPANION_SERVICE_URL'] == 'http://study-companion-service:8088'


def test_phase9_frontend_routes_and_env():
    routes = (ROOT / 'apps/web/src/router/routes.ts').read_text()
    assert "/capture" in routes
    assert "/tasks" in routes
    assert "/study-companion" in routes
    env = (ROOT / '.env.example').read_text()
    assert 'VITE_CAPTURE_URL=' in env
    assert 'VITE_STUDY_COMPANION_URL=' in env


def test_phase9_manifests_are_valid():
    for name in ['capture', 'tasks', 'study-companion']:
        manifest = yaml.safe_load((ROOT / f'modules/{name}/manifest.yaml').read_text())
        assert manifest['id'] == name
        assert manifest['sync']['enabled'] is True
