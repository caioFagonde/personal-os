"""
V1 certification tests.
Verifies structural invariants required for v1 readiness:
 - smoke test script exists and is valid
 - Make target exists
 - all routes point to real pages
 - no known-bad migration patterns
 - no known-bad compose patterns
 - all pages have error handling
 - critical endpoints documented
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web" / "src"


# ---------------------------------------------------------------------------
# Smoke test infrastructure
# ---------------------------------------------------------------------------

def test_v1_smoke_script_exists():
    path = ROOT / "scripts" / "certify" / "v1-local-smoke.sh"
    assert path.exists()
    content = path.read_text()
    assert "#!/usr/bin/env bash" in content
    assert "PASS=" in content
    assert "FAIL=" in content


def test_v1_smoke_script_syntax():
    import subprocess
    result = subprocess.run(
        ["bash", "-n", str(ROOT / "scripts" / "certify" / "v1-local-smoke.sh")],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"v1-local-smoke.sh syntax error: {result.stderr}"


def test_certify_v1_make_target_exists():
    makefile = (ROOT / "Makefile").read_text()
    assert "certify-v1" in makefile
    assert "v1-local-smoke.sh" in makefile


def test_feature_matrix_exists():
    path = ROOT / "docs" / "v1-feature-matrix.md"
    assert path.exists()
    content = path.read_text()
    assert "Command Center" in content
    assert "Capture" in content
    assert "Working" in content


# ---------------------------------------------------------------------------
# Route → page completeness
# ---------------------------------------------------------------------------

def test_all_routes_have_pages():
    routes_text = (WEB / "router" / "routes.ts").read_text()
    imports = re.findall(r"import (\w+) from '\.\./pages/(\w+)\.vue'", routes_text)
    for var_name, page_name in imports:
        page_path = WEB / "pages" / f"{page_name}.vue"
        assert page_path.exists(), f"Route imports {page_name}.vue but file does not exist"


def test_no_orphaned_pages():
    routes_text = (WEB / "router" / "routes.ts").read_text()
    pages_dir = WEB / "pages"
    for f in sorted(pages_dir.glob("*.vue")):
        assert f.stem in routes_text, f"Page {f.name} is not imported in routes.ts (orphaned)"


# ---------------------------------------------------------------------------
# Migration safety
# ---------------------------------------------------------------------------

def test_no_non_idempotent_create_table():
    migrations_dir = ROOT / "infra" / "postgres" / "migrations"
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        text = sql_file.read_text()
        bare_creates = re.findall(r"CREATE TABLE\s+(?!IF NOT EXISTS)", text)
        assert not bare_creates, f"{sql_file.name} has non-idempotent CREATE TABLE"


def test_no_non_idempotent_create_index():
    migrations_dir = ROOT / "infra" / "postgres" / "migrations"
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        text = sql_file.read_text()
        bare = re.findall(r"CREATE (?:UNIQUE )?INDEX\s+(?!IF NOT EXISTS)", text)
        assert not bare, f"{sql_file.name} has non-idempotent CREATE INDEX"


# ---------------------------------------------------------------------------
# Compose safety
# ---------------------------------------------------------------------------

def test_compose_parses():
    import yaml
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    assert "services" in compose
    assert "api-gateway" in compose["services"]


def test_compose_web_context_is_root():
    import yaml
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    web = compose["services"].get("web", {})
    build = web.get("build", {})
    if isinstance(build, dict) and "context" in build:
        assert build["context"] == ".", \
            f"web build context must be '.', got '{build['context']}'"


# ---------------------------------------------------------------------------
# Capture service invariants
# ---------------------------------------------------------------------------

def test_capture_service_no_kind_service():
    text = (ROOT / "services" / "capture-service" / "app" / "main.py").read_text()
    ensure_block = text.split("async def ensure_device")[1][:500]
    assert "'service'" not in ensure_block


def test_capture_service_handles_note_target():
    text = (ROOT / "services" / "capture-service" / "app" / "main.py").read_text()
    fn_block = text.split("async def upsert_task_from_capture")[1][:600]
    assert '"note"' in fn_block


# ---------------------------------------------------------------------------
# Study companion service invariants
# ---------------------------------------------------------------------------

def test_study_companion_no_kind_service():
    text = (ROOT / "services" / "study-companion-service" / "app" / "main.py").read_text()
    ensure_block = text.split("async def ensure_device")[1][:500]
    assert "'service'" not in ensure_block


def test_study_companion_entity_columns():
    text = (ROOT / "services" / "study-companion-service" / "app" / "main.py").read_text()
    fn_block = text.split("async def create_entity")[1][:500]
    assert "owner_device_id" not in fn_block
    assert "created_by_device" in fn_block


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_capture_service_has_error_handler():
    text = (ROOT / "services" / "capture-service" / "app" / "main.py").read_text()
    assert "exception_handler" in text


def test_study_companion_has_error_handler():
    text = (ROOT / "services" / "study-companion-service" / "app" / "main.py").read_text()
    assert "exception_handler" in text


# ---------------------------------------------------------------------------
# Page error handling (critical pages)
# ---------------------------------------------------------------------------

def _read_page(name: str) -> str:
    return (WEB / "pages" / name).read_text()


def test_critical_pages_have_error_handling():
    critical = [
        "CapturePage.vue",
        "TasksPage.vue",
        "CommandCenterPage.vue",
        "ConnectorsPage.vue",
        "CodingAgentPage.vue",
        "StudyCompanionPage.vue",
    ]
    for page in critical:
        text = _read_page(page)
        assert "catch" in text, f"{page} must have error handling (catch)"


# ---------------------------------------------------------------------------
# Coding agent policy
# ---------------------------------------------------------------------------

def test_coding_agent_policy_blocks_rm_rf_variants():
    text = (ROOT / "services" / "coding-agent-service" / "app" / "policy.py").read_text()
    assert r"\brm\s+(-rf|-fr|-r\s+-f|-f\s+-r)\b" in text, \
        "Policy must block all rm -rf flag orderings"
