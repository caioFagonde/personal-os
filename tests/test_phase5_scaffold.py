from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase5_files_exist():
    expected = [
        "infra/postgres/migrations/004_phase_5_research_maps_ar.sql",
        "services/research-service/app/main.py",
        "services/research-service/app/source_policy.py",
        "services/research-service/app/pdf_ingest.py",
        "services/module-service/app/ar_math.py",
        "apps/web/src/pages/ResearchPage.vue",
        "apps/web/src/pages/ARMemoryPage.vue",
        "scripts/maps/import-osm-pgrouting.sh",
        "docs/phase-5-research-maps-ar.md",
    ]
    for rel in expected:
        assert (ROOT / rel).exists(), rel


def test_no_pirate_connector_modules_are_present():
    forbidden_paths = ["libgen", "zlibrary", "z_library", "scihub", "sci_hub"]
    for path in ROOT.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            normalized = path.name.lower().replace("-", "_")
            assert not any(term in normalized for term in forbidden_paths), str(path)


def test_research_service_is_composed_and_proxied():
    compose = (ROOT / "docker-compose.yml").read_text()
    gateway = (ROOT / "services/api-gateway/app/main.py").read_text()
    assert "research-service:" in compose
    assert "RESEARCH_SERVICE_URL" in compose
    assert "/api/proxy/research" in gateway
