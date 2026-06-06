from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

def test_env_example_has_no_real_secret_markers():
    text = (ROOT / '.env.example').read_text()
    assert 'AIza' not in text
    assert 'sk-' not in text
    assert 'InsideGoogle' not in text

def test_module_manifests_have_required_fields():
    for path in (ROOT / 'modules').glob('*/manifest.yaml'):
        data = yaml.safe_load(path.read_text())
        for key in ['id', 'name', 'version', 'routes', 'permissions', 'events', 'storage', 'sync']:
            assert key in data, f'{path} missing {key}'
