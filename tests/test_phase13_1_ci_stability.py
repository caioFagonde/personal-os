from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_env_example_can_be_sourced_by_bash():
    text = (ROOT / '.env.example').read_text()
    forbidden = re.search(r'^FORBIDDEN_SOURCE_HOST_PATTERNS=(.*)$', text, re.M)
    assert forbidden, 'FORBIDDEN_SOURCE_HOST_PATTERNS is required'
    value = forbidden.group(1)
    assert value.startswith('"') and value.endswith('"'), 'values containing spaces must be quoted for source .env'


def test_quasar_index_has_entry_point_marker():
    index = (ROOT / 'apps/web/index.html').read_text()
    assert '<body>' in index
    assert '<!-- quasar:entry-point -->' in index
    assert '<div id="q-app"></div>' not in index


def test_workflows_do_not_use_invalid_python_module_invocation():
    for path in (ROOT / '.github/workflows').glob('*.yml'):
        text = path.read_text()
        assert 'python -m PYTHONPATH=.' not in text
        assert 'test -- --coverage' not in text
        assert 'test -- --run' not in text


def test_workflows_are_yaml_and_scaffold_jobs_install_pytest():
    for path in (ROOT / '.github/workflows').glob('*.yml'):
        yaml.safe_load(path.read_text())
    for path in [
        ROOT / '.github/workflows/phase10-connectors-continuity.yml',
        ROOT / '.github/workflows/phase12-certification-release.yml',
        ROOT / '.github/workflows/phase13-live-stack-model-release.yml',
    ]:
        text = path.read_text()
        assert 'pip install' in text and 'pytest' in text


def test_compose_uses_available_search_image_and_postgres_pgvector_strategy():
    compose = (ROOT / 'docker-compose.yml').read_text()
    assert 'searxng/searxng:2024.11.11-333bb36' not in compose
    assert 'searxng/searxng:latest' in compose
    dockerfile = (ROOT / 'infra/postgres/Dockerfile').read_text()
    assert 'postgresql-16-pgvector' in dockerfile
    assert 'clang-13' in dockerfile
