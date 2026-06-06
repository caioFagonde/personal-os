from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_compose_profile_dependencies_are_enabled_together():
    compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
    services = compose['services']
    profile_services = {}
    for name, service in services.items():
        for profile in service.get('profiles', []):
            profile_services.setdefault(profile, set()).add(name)
    for profile, active in profile_services.items():
        for name in list(active):
            for dep in services[name].get('depends_on', {}) or {}:
                assert dep in active, f'{name} depends on {dep}, but {dep} is not active in profile {profile}'


def test_phase8_migration_adds_storage_tables_before_using_it():
    sql = (ROOT / 'infra/postgres/migrations/007_phase_8_digital_twin.sql').read_text()
    assert 'ALTER TABLE modules ADD COLUMN IF NOT EXISTS storage_tables' in sql
    assert sql.index('ALTER TABLE modules ADD COLUMN IF NOT EXISTS storage_tables') < sql.index('INSERT INTO modules')


def test_workflows_do_not_require_absent_pnpm_lock_for_setup_node_cache():
    for path in (ROOT / '.github/workflows').glob('*.yml'):
        text = path.read_text()
        assert 'cache: pnpm' not in text
        assert "cache: 'pnpm'" not in text
        assert 'FORCE_JAVASCRIPT_ACTIONS_TO_NODE24' in text


def test_twilio_provider_is_optional_and_never_commits_phone_numbers():
    env = (ROOT / '.env.example').read_text()
    assert 'WHATSAPP_PROVIDER=cloud_api' in env
    assert 'TWILIO_ACCOUNT_SID=' in env
    assert 'TWILIO_AUTH_TOKEN=' in env
    assert '+551' not in env
    delegation = (ROOT / 'services/capture-service/app/delegation.py').read_text()
    assert 'whatsapp.twilio_sandbox' in delegation
    assert 'whatsapp.cloud_api' in delegation
