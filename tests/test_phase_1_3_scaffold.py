from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase_migration_exists():
    assert (ROOT / "infra/postgres/migrations/002_phase_1_2_3.sql").exists()


def test_module_service_exists_and_is_composed():
    assert (ROOT / "services/module-service/app/main.py").exists()
    compose = (ROOT / "docker-compose.yml").read_text()
    assert "module-service:" in compose
    assert "MODULE_SERVICE_PORT" in compose


def test_web_has_real_module_pages():
    for page in ["StudyPage.vue", "ZettelkastenPage.vue", "GeospatialPage.vue"]:
        assert (ROOT / "apps/web/src/pages" / page).exists()
