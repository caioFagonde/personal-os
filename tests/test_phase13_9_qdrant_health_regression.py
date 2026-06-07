from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_qdrant_does_not_gate_full_stack_on_brittle_container_healthcheck():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    qdrant = compose["services"]["qdrant"]
    assert "healthcheck" not in qdrant, "Qdrant healthcheck should not depend on curl/wget inside upstream image"

    embeddings = compose["services"]["embeddings"]
    assert embeddings["depends_on"]["qdrant"]["condition"] == "service_started"


def test_qdrant_has_host_side_doctor_script():
    script = ROOT / "scripts" / "doctor-qdrant.sh"
    text = script.read_text()
    assert "QDRANT_URL" in text
    assert "curl -fsS" in text
    assert "docker compose logs --tail=120 qdrant" in text
