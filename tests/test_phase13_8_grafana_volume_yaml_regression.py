from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_grafana_volumes_are_separate_yaml_list_items():
    compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
    volumes = compose['services']['grafana']['volumes']
    assert './infra/observability/grafana/provisioning:/etc/grafana/provisioning:ro' in volumes
    assert './infra/observability/grafana/dashboards:/var/lib/grafana/dashboards:ro' in volumes
    for volume in volumes:
        assert ' - ./infra/observability/grafana/dashboards:' not in volume
        assert volume.count(':') <= 2, volume
