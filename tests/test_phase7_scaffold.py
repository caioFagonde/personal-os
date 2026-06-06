from pathlib import Path
import json
import yaml

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_phase7_migration_contains_required_tables():
    sql = read('infra/postgres/migrations/006_phase_7_production_ux.sql')
    for table in [
        'service_identities',
        'durable_event_consumers',
        'release_channels',
        'client_sync_state',
        'ux_preferences',
        'telemetry_events',
        'service_health_snapshots',
    ]:
        assert f'CREATE TABLE IF NOT EXISTS {table}' in sql


def test_observability_profile_contains_otel_and_grafana_dashboard():
    compose = yaml.safe_load(read('docker-compose.yml'))
    services = compose['services']
    assert 'otel-collector' in services
    assert 'observability' in services['otel-collector']['profiles']
    assert any('grafana/provisioning' in v for v in services['grafana']['volumes'])
    assert (ROOT / 'infra/observability/grafana/dashboards/control-plane.json').exists()


def test_web_shell_has_command_palette_mobile_nav_and_design_tokens():
    app = read('apps/web/src/App.vue')
    assert 'CommandPalette' in app
    assert 'BottomNav' in app
    assert 'safeAreaStyle' in app
    css = read('apps/web/src/css/app.scss')
    assert '--nexus-accent' in css
    assert 'prefers-reduced-motion' in css
    assert 'safe-area-inset-bottom' in css


def test_mobile_and_desktop_have_native_policy_tests():
    assert (ROOT / 'apps/mobile/src/runtime-policy.ts').exists()
    assert (ROOT / 'apps/mobile/tests/runtime-policy.test.ts').exists()
    assert 'validate_deep_link' in read('apps/desktop/src-tauri/src/main.rs')
    assert 'javascript:alert(1)' in read('apps/desktop/src-tauri/src/lib.rs')


def test_phase7_workflows_are_split_and_actionable():
    workflow = yaml.safe_load(read('.github/workflows/phase7-production-ux.yml'))
    jobs = workflow['jobs']
    for job in ['service-identity-observability', 'design-system-and-web-ux', 'mobile-preflight', 'desktop-native-tests', 'observability-compose-contract']:
        assert job in jobs
    release = yaml.safe_load(read('.github/workflows/release.yml'))
    assert {'web-artifact', 'android-debug-artifact', 'desktop-tauri-artifact'} <= set(release['jobs'])


def test_tauri_config_is_upgraded_for_desktop_ux():
    conf = json.loads(read('apps/desktop/src-tauri/tauri.conf.json'))
    window = conf['app']['windows'][0]
    assert window['width'] >= 1440
    assert window['minWidth'] >= 1024
    assert conf['version'] == '0.7.0'


def test_release_manifest_tool_exists_and_is_executable():
    script = ROOT / 'scripts/release/build-manifest.py'
    assert script.exists()
    assert script.stat().st_mode & 0o111
