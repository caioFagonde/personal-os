from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_phase8_migration_contains_digital_twin_tables():
    sql = read('infra/postgres/migrations/007_phase_8_digital_twin.sql')
    for table in [
        'digital_twin_entities',
        'digital_twin_relationships',
        'digital_twin_timeline_events',
        'digital_twin_state_snapshots',
        'digital_twin_goals',
        'digital_twin_recommendation_runs',
        'digital_twin_memory_policies',
        'digital_twin_memory_records',
        'digital_twin_model_evaluations',
        'digital_twin_intervention_outcomes',
    ]:
        assert f'CREATE TABLE IF NOT EXISTS {table}' in sql


def test_digital_twin_service_is_wired_in_compose_and_gateway():
    compose = yaml.safe_load(read('docker-compose.yml'))
    service = compose['services']['digital-twin-service']
    assert service['container_name'] == 'personal-os-digital-twin-service'
    assert 'ai' in service['profiles']
    gateway = read('services/api-gateway/app/main.py')
    assert 'DIGITAL_TWIN_SERVICE_URL' in gateway
    assert '/api/proxy/digital-twin/{path:path}' in gateway
    assert 'digital_twin:read' in gateway
    assert 'recommendations:write' in gateway


def test_digital_twin_manifest_and_web_route_exist():
    manifest = yaml.safe_load(read('modules/digital-twin/manifest.yaml'))
    assert manifest['id'] == 'digital-twin'
    assert manifest['routes']['web'] == '/digital-twin'
    assert 'digital_twin:write' in manifest['permissions']
    assert (ROOT / 'apps/web/src/pages/DigitalTwinPage.vue').exists()
    routes = read('apps/web/src/router/routes.ts')
    assert '/digital-twin' in routes
    assert 'DigitalTwinPage' in routes


def test_makefile_and_workflow_have_phase8_targets():
    makefile = read('Makefile')
    assert 'up-digital-twin' in makefile
    assert 'test-phase8' in makefile
    workflow = yaml.safe_load(read('.github/workflows/phase8-digital-twin.yml'))
    assert {'digital-twin-coverage', 'scaffold-contract', 'compose-contract', 'web-digital-twin-contract'} <= set(workflow['jobs'])


def test_docs_and_env_include_phase8():
    assert (ROOT / 'docs/phase-8-digital-twin-intelligence.md').exists()
    env = read('.env.example')
    assert 'DIGITAL_TWIN_SERVICE_PORT=8086' in env
    assert 'VITE_DIGITAL_TWIN_URL=' in env
