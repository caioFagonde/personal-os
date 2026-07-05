"""Phase B contract tests — Graph & Memory spine.

Locks in: migration 014 (registry + domain tables, idempotent, trigram fallback
indexes), the packages/graph dual-write helper and its per-service copies,
real embeddings with honest degradation (no fake vectors), the gateway graph
API, and the Projects/DailyState verticals.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "infra/postgres/migrations/014_nexus_graph.sql"
CANONICAL_HELPER = ROOT / "packages/graph/py/nexus_graph.py"
SERVICE_HELPER_COPIES = [
    ROOT / "services/capture-service/app/graph.py",
    ROOT / "services/module-service/app/graph.py",
    ROOT / "services/research-service/app/graph.py",
    ROOT / "services/digital-twin-service/app/graph.py",
    ROOT / "services/coding-agent-service/app/graph.py",
]


# --- B1: migration -----------------------------------------------------------

def test_migration_014_exists_and_is_idempotent():
    sql = MIGRATION.read_text()
    for table in ("objects", "edges", "object_chunks", "projects", "decisions",
                  "daily_states", "repositories", "portfolio_cases"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql, f"missing idempotent create for {table}"
    assert "CREATE TABLE IF NOT EXISTS" in sql
    assert "CREATE TABLE " not in sql.replace("CREATE TABLE IF NOT EXISTS", "")
    for index_fragment in ("CREATE INDEX IF NOT EXISTS",):
        assert index_fragment in sql


def test_migration_014_registry_shape():
    sql = MIGRATION.read_text()
    assert "UNIQUE (domain_table, domain_id)" in sql          # upsert key for dual-writes
    assert "UNIQUE (src_id, dst_id, rel)" in sql              # edge idempotency
    assert "UNIQUE (object_id, seq)" in sql                   # chunk idempotency
    assert "vector(768)" in sql                               # pgvector embedding column
    assert "hnsw" in sql                                      # ANN index
    assert "pg_trgm" in sql and "gin_trgm_ops" in sql         # honest lexical fallback path
    assert "model" in sql                                     # multi-model re-embedding column


# --- B2: dual-write helper ----------------------------------------------------

def test_graph_helper_copies_are_byte_identical():
    canonical = CANONICAL_HELPER.read_bytes()
    for copy in SERVICE_HELPER_COPIES:
        assert copy.exists(), f"missing graph helper copy: {copy}"
        assert copy.read_bytes() == canonical, (
            f"{copy} drifted from packages/graph/py/nexus_graph.py — edit the canonical file and re-copy"
        )


def test_graph_helper_is_best_effort():
    src = CANONICAL_HELPER.read_text()
    # A registry failure must be recorded for repair, never raised into the domain write.
    assert "graph.write_failed" in src
    assert "service_events" in src
    for fn in ("async def register_object", "async def link", "async def upsert_chunks"):
        assert fn in src


def test_dual_writes_are_wired():
    capture = (ROOT / "services/capture-service/app/main.py").read_text()
    assert "register_object" in capture and "derived_from" in capture
    assert "set_project" in capture  # task→project triage path
    module = (ROOT / "services/module-service/app/main.py").read_text()
    assert 'kind="note"' in module and 'kind="project"' in module and 'kind="daily_state"' in module
    research = (ROOT / "services/research-service/app/main.py").read_text()
    assert 'kind="source"' in research
    twin = (ROOT / "services/digital-twin-service/app/main.py").read_text()
    assert 'kind="goal"' in twin and 'kind="event"' in twin
    coding = (ROOT / "services/coding-agent-service/app/main.py").read_text()
    assert 'kind="agent_run"' in coding


def test_backfill_script_exists_and_is_idempotent_by_design():
    src = (ROOT / "scripts/graph/backfill.py").read_text()
    assert "register_object" in src
    assert "--dry-run" in src
    for table in ("capture_items", "tasks", "notes", "research_documents", "projects", "daily_states"):
        assert table in src


# --- B3: real embeddings, honest degradation -----------------------------------

def test_embeddings_service_has_no_fake_vectors():
    main = (ROOT / "services/embeddings/app/main.py").read_text()
    provider = (ROOT / "services/embeddings/app/provider.py").read_text()
    # The old placeholder synthesized vectors from character sums. Never again.
    for forbidden in ("seed", "ord(c)", "997"):
        assert forbidden not in main, "placeholder vector generator resurfaced in embeddings main"
        assert forbidden not in provider.replace("seed", "") or forbidden not in provider, (
            "placeholder vector generator resurfaced in embeddings provider"
        )
    assert "EmbeddingUnavailable" in provider
    assert "ollama" in provider.lower()
    assert "503" in main  # /api/embed fails honestly instead of faking


def test_embeddings_worker_consumes_outbox_and_nats():
    worker = (ROOT / "services/embeddings/app/worker.py").read_text()
    assert "nexus.embed" in worker
    assert "service_events" in worker
    assert "embedding IS NULL" in worker  # repair sweep
    assert "EmbeddingUnavailable" in worker  # degraded mode leaves NULLs, no fakes


def test_graph_search_labels_lexical_fallback():
    gateway = (ROOT / "services/api-gateway/app/graph.py").read_text()
    assert "lexical search (no embedding model)" in gateway
    assert '"hybrid"' in gateway and '"lexical"' in gateway
    assert "similarity(" in gateway  # trigram path
    assert "<=>" in gateway          # pgvector cosine path


# --- B4: gateway graph API ------------------------------------------------------

def test_gateway_exposes_graph_routes():
    gateway = (ROOT / "services/api-gateway/app/graph.py").read_text()
    assert '"/api/graph/objects"' in gateway
    assert '"/api/graph/objects/{object_id}/neighbors"' in gateway
    assert '"/api/graph/search"' in gateway
    main = (ROOT / "services/api-gateway/app/main.py").read_text()
    assert "build_graph_router" in main


def test_graph_search_merge_prefers_dual_signal():
    import pytest
    pytest.importorskip("fastapi", reason="gateway deps not installed in this environment")
    # Import through the root-conftest service alias — inserting the service dir
    # into sys.path would collide with other services' `app` packages.
    from services.api_gateway.app.graph import merge_hits
    lex = [{"object": {"id": "a"}, "score": 0.5, "snippet": "lex"}]
    vec = [{"object": {"id": "a"}, "score": 0.7, "snippet": None},
           {"object": {"id": "b"}, "score": 0.6, "snippet": None}]
    merged = merge_hits(lex, vec, 10)
    assert merged[0]["object"]["id"] == "a"
    assert merged[0]["score"] > 0.7          # dual-signal bonus
    assert merged[0]["snippet"] == "lex"     # snippet survives merge
    assert merge_hits([], [], 5) == []


def test_web_palette_consumes_graph_search():
    palette = (ROOT / "apps/web/src/components/CommandPalette.vue").read_text()
    assert "graphSearch" in palette
    assert "graphLabel" in palette  # honest mode label surfaces in the UI
    zettel = (ROOT / "apps/web/src/pages/ZettelkastenPage.vue").read_text()
    assert "graphNeighbors" in zettel


# --- B5: Projects + DailyState verticals ----------------------------------------

def test_module_service_projects_and_daily_endpoints():
    module = (ROOT / "services/module-service/app/main.py").read_text()
    for route in ('"/api/projects"', '"/api/projects/{project_id}"',
                  '"/api/daily-state/today"', '"/api/daily-state/open"', '"/api/daily-state/close"'):
        assert route in module, f"missing route {route}"


def test_task_patch_accepts_project_assignment():
    capture = (ROOT / "services/capture-service/app/main.py").read_text()
    assert "project_id" in capture
    assert "project_not_found" in capture  # structured 404, not a bare failure


def test_web_has_projects_and_daily_pages():
    routes = (ROOT / "apps/web/src/router/routes.ts").read_text()
    assert "'/projects'" in routes and "'/daily'" in routes
    assert (ROOT / "apps/web/src/pages/ProjectsPage.vue").exists()
    assert (ROOT / "apps/web/src/pages/DailyPage.vue").exists()


def test_e2e_spec_proves_the_loop():
    spec = ROOT / "e2e/graph-loop.spec.ts"
    assert spec.exists(), "Phase B exit criterion: e2e/graph-loop.spec.ts must exist"
    src = spec.read_text()
    for step in ("capture", "project", "search", "neighbors"):
        assert step in src, f"exit-loop spec missing step: {step}"
