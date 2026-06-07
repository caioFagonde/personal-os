from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_quasar_index_uses_marker_without_legacy_q_app_div():
    html = (ROOT / 'apps/web/index.html').read_text()
    assert '<!-- quasar:entry-point -->' in html
    assert '<div id="q-app"></div>' not in html


def test_otel_uses_debug_exporter_not_deprecated_logging_exporter():
    cfg = yaml.safe_load((ROOT / 'infra/observability/otel-collector.yml').read_text())
    assert 'debug' in cfg['exporters']
    assert 'logging' not in cfg['exporters']
    for pipeline in cfg['service']['pipelines'].values():
        assert 'logging' not in pipeline.get('exporters', [])


def test_n8n_isolated_from_personal_os_public_tables():
    compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
    n8n = compose['services']['n8n']
    env = n8n['environment']
    assert env.get('DB_TABLE_PREFIX') == 'n8n_'
    assert 'n8n_data:/home/node/.n8n' in n8n.get('volumes', [])
    assert env.get('N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS') == 'true'


def test_searxng_has_non_default_secret_and_writable_config_mount():
    compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
    searx = compose['services']['searxng']
    assert searx['environment']['SEARXNG_SECRET'].startswith('${SEARXNG_SECRET')
    assert './infra/searxng:/etc/searxng' in searx.get('volumes', [])
    assert './infra/searxng:/etc/searxng:ro' not in searx.get('volumes', [])
    settings = (ROOT / 'infra/searxng/settings.yml').read_text()
    assert 'secret_key:' in settings
    assert 'ultrasecretkey' not in settings


def test_tileserver_can_write_demo_or_local_mbtiles_to_maps_directory():
    compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
    tileserver = compose['services']['tileserver']
    assert './data/maps:/data' in tileserver.get('volumes', [])
    assert './data/maps:/data:ro' not in tileserver.get('volumes', [])


def test_env_generator_creates_searxng_secret():
    generator = (ROOT / 'scripts/generate-env.py').read_text()
    example = (ROOT / '.env.example').read_text()
    assert 'SEARXNG_SECRET' in generator
    assert 'SEARXNG_SECRET=<generate-with-openssl-rand-hex-32>' in example
