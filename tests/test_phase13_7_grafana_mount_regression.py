from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_grafana_dashboard_json_mount_does_not_nest_under_read_only_provisioning():
    compose = (ROOT / 'docker-compose.yml').read_text()
    assert './infra/observability/grafana/provisioning:/etc/grafana/provisioning:ro' in compose
    assert '/etc/grafana/provisioning/dashboards/json' not in compose
    assert './infra/observability/grafana/dashboards:/var/lib/grafana/dashboards:ro' in compose


def test_grafana_dashboard_provider_points_to_data_dashboard_path():
    provider = (ROOT / 'infra/observability/grafana/provisioning/dashboards/personal-os.yml').read_text()
    assert 'path: /var/lib/grafana/dashboards' in provider
    assert '/etc/grafana/provisioning/dashboards/json' not in provider
