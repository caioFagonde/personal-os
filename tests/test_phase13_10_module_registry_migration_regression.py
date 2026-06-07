from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "infra/postgres/migrations/011_phase_13_live_stack_model_runtime.sql"


def test_phase13_model_runtime_upsert_uses_existing_modules_schema():
    sql = MIGRATION.read_text()
    insert_section = sql.split("INSERT INTO modules", 1)[1]
    assert "events," not in insert_section.split(")", 1)[0]
    assert "sync_strategy" not in insert_section.split(")", 1)[0]
    assert "manifest" in insert_section.split(")", 1)[0]
    assert "publishes" in insert_section.split(")", 1)[0]
    assert "subscribes" in insert_section.split(")", 1)[0]


def test_phase13_model_runtime_manifest_keeps_event_and_sync_metadata():
    sql = MIGRATION.read_text()
    assert '"events"' in sql
    assert '"publishes"' in sql
    assert '"subscribes"' in sql
    assert '"sync"' in sql
    assert '"strategy": "local-first"' in sql
