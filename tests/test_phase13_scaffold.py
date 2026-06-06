from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_model_runtime_service_is_wired():
    assert (ROOT / 'services/model-runtime/app/runtime.py').exists()
    compose = read('docker-compose.yml')
    assert 'personal-os-model-runtime' in compose
    assert 'MODEL_RUNTIME_SERVICE_URL' in compose
    assert 'VITE_MODEL_RUNTIME_URL' in compose
    gateway = read('services/api-gateway/app/main.py')
    assert '/api/proxy/model-runtime/{path:path}' in gateway
    assert 'model_runtime:write' in gateway


def test_phase13_ui_surfaces_exist():
    for path in [
        'apps/web/src/pages/ModelRuntimePage.vue',
        'apps/web/src/pages/LiveStackPage.vue',
        'apps/web/src/pages/InitialVersionReadinessPage.vue',
    ]:
        assert (ROOT / path).exists()
    routes = read('apps/web/src/router/routes.ts')
    for route in ['/model-runtime', '/live-stack', '/initial-readiness']:
        assert route in routes
    nav = read('apps/web/src/design/tokens.ts')
    assert 'Model Runtime' not in nav  # labels are concise in nav
    assert 'model-runtime' in nav


def test_phase13_certification_scripts_exist_and_are_executable():
    for path in [
        'scripts/certify/live-stack-e2e.sh',
        'scripts/certify/physical-sync.sh',
        'scripts/certify/model-runtime.sh',
        'scripts/certify/release-readiness.py',
        'scripts/release/publish-github-release.sh',
    ]:
        p = ROOT / path
        assert p.exists()
        assert p.stat().st_mode & 0o111
    assert 'adb reverse' in read('scripts/certify/physical-sync.sh')
    assert 'playwright test e2e/live-stack.spec.ts' in read('scripts/certify/live-stack-e2e.sh')


def test_phase13_workflow_and_e2e_are_present():
    workflow = yaml.safe_load(read('.github/workflows/phase13-live-stack-model-release.yml'))
    assert workflow['name'].startswith('Phase 13')
    assert 'live-stack-e2e' in workflow['jobs']
    assert 'model-runtime-coverage' in workflow['jobs']
    e2e = read('e2e/live-stack.spec.ts')
    assert '/api/proxy/model-runtime/api/model-runtime/process-text' in e2e


def test_phase13_migration_and_manifest_are_present():
    migration = read('infra/postgres/migrations/011_phase_13_live_stack_model_runtime.sql')
    assert 'model_runtime_invocations' in migration
    assert 'certification_runs' in migration
    manifest = yaml.safe_load(read('modules/model-runtime/manifest.yaml'))
    assert manifest['id'] == 'model-runtime'
    assert 'model_runtime:write' in manifest['permissions']
