from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_coding_agent_scaffold_exists():
    assert (ROOT / "services/coding-agent-service/app/main.py").exists()
    assert (ROOT / "services/coding-agent-service/app/policy.py").exists()
    assert (ROOT / "modules/coding-agent/manifest.yaml").exists()
    assert (ROOT / "apps/web/src/pages/CodingAgentPage.vue").exists()


def test_compose_wires_coding_agent_and_gateway():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    service = compose["services"]["coding-agent-service"]
    assert service["ports"] == ["${CODING_AGENT_SERVICE_PORT:-8096}:8096"]
    gateway_env = compose["services"]["api-gateway"]["environment"]
    assert gateway_env["CODING_AGENT_SERVICE_URL"] == "http://coding-agent-service:8096"
    web_env = compose["services"]["web"]["environment"]
    assert "VITE_CODING_AGENT_URL" in web_env


def test_api_gateway_has_coding_agent_proxy_and_scopes():
    text = (ROOT / "services/api-gateway/app/main.py").read_text()
    assert "CODING_AGENT_SERVICE_URL" in text
    assert "coding_agent:read" in text
    assert "/api/proxy/coding-agent/{path:path}" in text


def test_oauth_device_flow_endpoints_exist():
    text = (ROOT / "services/connector-service/app/main.py").read_text()
    assert "/api/connectors/{provider}/device/start" in text
    assert "/api/connectors/{provider}/device/poll" in text
    assert "connector_device_flows" in text


def test_visual_system_defines_glass_card():
    css = (ROOT / "apps/web/src/css/app.scss").read_text()
    assert ".glass-card" in css
    assert "color: var(--nexus-text)" in css
    assert "background: linear-gradient" in css


def test_command_center_is_default_route():
    routes = (ROOT / "apps/web/src/router/routes.ts").read_text()
    assert "CommandCenterPage" in routes
    assert "{ path: '/', component: CommandCenterPage }" in routes
    tokens = (ROOT / "apps/web/src/design/tokens.ts").read_text()
    assert "coding-agent" in tokens
    assert "Command Center" in tokens


def test_phase14_migration_exists_and_is_schema_compatible():
    text = (ROOT / "infra/postgres/migrations/012_phase_14_oauth_coding_agent_command_center.sql").read_text()
    assert "connector_device_flows" in text
    assert "coding_agent_jobs" in text
    assert "INSERT INTO modules(" in text
    assert "events," not in text
    assert "sync_strategy" not in text


def test_coding_agent_page_has_error_handling():
    text = (ROOT / "apps/web/src/pages/CodingAgentPage.vue").read_text()
    # Error banners are rendered when backend is unreachable
    assert "loadError" in text
    assert "actionError" in text
    assert "q-banner" in text
    # Execution requires approval — pending_approval jobs must not show Execute
    assert "pending_approval" in text
    assert "confirmRun" in text or "confirmDialog" in text
    # Result is structured, not a raw JSON blob
    assert "runResult.stdout" in text
    assert "runResult.stderr" in text
    assert "runResult.artifacts" in text


def test_connectors_page_has_full_error_handling():
    text = (ROOT / "apps/web/src/pages/ConnectorsPage.vue").read_text()
    # All async side-effects are wrapped in try/catch
    assert "testTwilio" in text
    assert "testNtfy" in text
    assert "checkTailscale" in text
    # Each wraps in try/catch, not bare await
    twilio_block = text[text.index("async function testTwilio"):]
    ntfy_block = text[text.index("async function testNtfy"):]
    tailscale_block = text[text.index("async function checkTailscale"):]
    assert "catch" in twilio_block[:300]
    assert "catch" in ntfy_block[:300]
    assert "catch" in tailscale_block[:300]
    # Load errors surface to the user
    assert "loadError" in text
    assert "q-banner" in text


def test_service_source_files_have_no_ambiguous_variable_names():
    acquisition = (ROOT / "services/research-service/app/acquisition.py").read_text()
    # Ruff E741: ambiguous name 'l' must not appear
    import re
    assert not re.search(r"\bfor l in\b", acquisition)
    companion = (ROOT / "services/study-companion-service/app/main.py").read_text()
    assert not re.search(r"\bfor l in\b", companion)


def test_service_source_files_have_no_known_unused_imports():
    # RunStatus was unused in automation-service
    automation = (ROOT / "services/automation-service/app/main.py").read_text()
    assert "RunStatus" not in automation.split("from .models import")[1].split("\n")[0]
    # Vec3 was unused in module-service
    module = (ROOT / "services/module-service/app/main.py").read_text()
    assert "Vec3" not in module.split("from .ar_math import")[1].split("\n")[0]


# ---------------------------------------------------------------------------
# RC Certification: coding-agent policy hardening
# ---------------------------------------------------------------------------

def test_coding_agent_policy_blocks_rm_rf_variants():
    import re as _re
    policy_text = (ROOT / "services/coding-agent-service/app/policy.py").read_text()
    # Extract raw pattern strings from the DANGEROUS_PROMPT_PATTERNS list literal
    raw = _re.findall(r'r"([^"]+)"', policy_text.split("DANGEROUS_PROMPT_PATTERNS")[1].split("]")[0])
    patterns = [_re.compile(p, _re.IGNORECASE) for p in raw]
    blocked = lambda p: any(pat.search(p) for pat in patterns)

    # All rm -rf forms must be blocked
    assert blocked("rm -rf ~/workspace"), "rm -rf ~/workspace must be blocked"
    assert blocked("rm -rf ./data"),      "rm -rf ./data must be blocked"
    assert blocked("rm -fr /tmp"),        "rm -fr /tmp must be blocked"
    assert blocked("rm -r -f /home"),     "rm -r -f /home must be blocked"
    assert blocked("rm -f -r /home"),     "rm -f -r /home must be blocked"
    assert blocked("rm -rf *"),           "rm -rf * must be blocked"
    # Root variant still blocked
    assert blocked("rm -rf /"),           "rm -rf / must still be blocked"
    # Safe commands must not be blocked
    assert not blocked("git commit -m fix"), "git commit must not be blocked"
    assert not blocked("please analyze this file"), "analysis prompt must not be blocked"


# ---------------------------------------------------------------------------
# RC Certification: navigation completeness
# ---------------------------------------------------------------------------

def test_sync_health_in_navigation_tokens():
    tokens_text = (ROOT / "apps/web/src/design/tokens.ts").read_text()
    assert "'sync-health'" in tokens_text or '"sync-health"' in tokens_text, (
        "sync-health must be in navigationModules so it is reachable from the sidebar"
    )


def test_no_orphaned_page_files():
    routes_text = (ROOT / "apps/web/src/router/routes.ts").read_text()
    pages_dir = ROOT / "apps/web/src/pages"
    # Any .vue file in pages/ whose class name is not imported in routes.ts is orphaned
    orphans = []
    for f in sorted(pages_dir.glob("*.vue")):
        if f.stem not in routes_text:
            orphans.append(f.name)
    # ModulePage is rendered via dynamic /modules/:id — expected
    allowed_orphans = {"ModulePage"}
    real_orphans = [o for o in orphans if o.replace(".vue", "") not in allowed_orphans]
    assert not real_orphans, f"Orphaned page files not in routes.ts: {real_orphans}"
