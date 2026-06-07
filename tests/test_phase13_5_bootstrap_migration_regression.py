from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_migration_004_does_not_use_expression_inside_inline_unique_constraint():
    sql = (ROOT / "infra/postgres/migrations/004_phase_5_research_maps_ar.sql").read_text()
    assert "UNIQUE(run_id, source, COALESCE" not in sql
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_research_search_results_dedupe" in sql
    assert "ON research_search_results (run_id, source, COALESCE(doi, ''), COALESCE(landing_url, ''), title)" in sql


def test_no_inline_unique_constraint_contains_coalesce_in_migrations():
    offenders = []
    for migration in (ROOT / "infra/postgres/migrations").glob("*.sql"):
        for line_no, line in enumerate(migration.read_text().splitlines(), 1):
            compact = line.strip().upper().replace(" ", "")
            if compact.startswith("UNIQUE(") and "COALESCE(" in compact:
                offenders.append(f"{migration.relative_to(ROOT)}:{line_no}:{line.strip()}")
    assert offenders == []
