"""
Phase 15 UX polish regression tests.
Verifies page-level safety contracts, error-handling patterns,
CSS invariants, and mobile layout requirements.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web" / "src"
CSS = (WEB / "css" / "app.scss").read_text()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def read_page(name: str) -> str:
    return (WEB / "pages" / name).read_text()


def read_component(name: str) -> str:
    return (WEB / "components" / name).read_text()


# ---------------------------------------------------------------------------
# CSS contracts
# ---------------------------------------------------------------------------

def test_action_grid_is_mobile_safe():
    # minmax must use min(100%, ...) to prevent overflow on narrow screens
    assert "minmax(min(100%" in CSS, (
        ".action-grid minmax must use min(100%, ...) to prevent horizontal overflow on mobile"
    )


def test_glass_card_has_dark_background():
    assert ".glass-card" in CSS
    assert "linear-gradient" in CSS


def test_hero_panel_defined():
    assert ".hero-panel" in CSS


def test_code_block_defined():
    assert ".code-block" in CSS


def test_dark_theme_text_variable_set():
    assert "--nexus-text" in CSS
    assert "--nexus-muted" in CSS
    assert "--nexus-accent" in CSS


def test_mobile_nav_defined():
    assert ".mobile-nav" in CSS


# ---------------------------------------------------------------------------
# CapturePage — error handling
# ---------------------------------------------------------------------------

def test_capture_page_has_error_handling():
    text = read_page("CapturePage.vue")
    assert "error" in text.lower()
    assert "try" in text
    assert "catch" in text
    assert "q-banner" in text


def test_capture_page_has_keyboard_shortcut():
    text = read_page("CapturePage.vue")
    assert "ctrl.enter" in text or "keydown" in text


def test_capture_page_has_secretary_template():
    text = read_page("CapturePage.vue")
    assert "/secretary" in text


def test_capture_page_has_hero_panel():
    text = read_page("CapturePage.vue")
    assert "hero-panel" in text or "eyebrow" in text


# ---------------------------------------------------------------------------
# TasksPage — error handling and task creation
# ---------------------------------------------------------------------------

def test_tasks_page_has_error_handling():
    text = read_page("TasksPage.vue")
    assert "error" in text.lower()
    assert "try" in text
    assert "catch" in text
    assert "q-banner" in text


def test_tasks_page_has_new_task_form():
    text = read_page("TasksPage.vue")
    assert "createTask" in text
    assert "POST" in text
    assert "title" in text


def test_tasks_page_has_filter_tabs():
    text = read_page("TasksPage.vue")
    assert "inbox" in text
    assert "delegated" in text


def test_tasks_page_has_complete_action():
    text = read_page("TasksPage.vue")
    assert "complete" in text
    assert "PATCH" in text


# ---------------------------------------------------------------------------
# StudyCompanionPage — error handling and result panel
# ---------------------------------------------------------------------------

def test_study_companion_has_error_handling():
    text = read_page("StudyCompanionPage.vue")
    assert "error" in text.lower()
    assert "try" in text
    assert "catch" in text
    assert "q-banner" in text


def test_study_companion_no_raw_json_dump():
    text = read_page("StudyCompanionPage.vue")
    # The raw JSON.stringify dump in a result-json block is gone
    assert "result-json" not in text
    assert "JSON.stringify(result" not in text


def test_study_companion_has_structured_result_panel():
    text = read_page("StudyCompanionPage.vue")
    assert "result.title" in text or "result.popup_note" in text
    assert "result.atoms" in text


def test_study_companion_analog_has_file_picker():
    text = read_page("StudyCompanionPage.vue")
    assert "q-file" in text
    assert "ingestAnalog" in text


# ---------------------------------------------------------------------------
# ConnectorsPage — setup instructions and structured output
# ---------------------------------------------------------------------------

def test_connectors_page_has_setup_instructions():
    text = read_page("ConnectorsPage.vue")
    assert "GOOGLE_CLIENT_ID" in text
    assert "MICROSOFT_CLIENT_ID" in text
    assert "restart connector-service" in text or "restart" in text


def test_connectors_page_ntfy_subscription_help():
    text = read_page("ConnectorsPage.vue")
    assert "ntfy" in text.lower()
    assert "subscription" in text.lower() or "subscribe" in text.lower() or "mobile" in text.lower()


def test_connectors_page_tailscale_ip_display():
    text = read_page("ConnectorsPage.vue")
    assert "tailscaleDetail" in text
    assert "hostname" in text or "ip" in text


def test_connectors_page_no_unguarded_test_calls():
    text = read_page("ConnectorsPage.vue")
    # All test functions must have try/catch
    for fn_name in ["testTwilio", "testNtfy", "checkTailscale"]:
        start = text.find(f"async function {fn_name}")
        if start < 0:
            continue
        block = text[start:start + 400]
        assert "catch" in block, f"{fn_name} must have error handling"


def test_connectors_page_load_error_banner():
    text = read_page("ConnectorsPage.vue")
    assert "loadError" in text
    assert "q-banner" in text


# ---------------------------------------------------------------------------
# CommandCenterPage — quick actions and sections
# ---------------------------------------------------------------------------

def test_command_center_has_quick_actions():
    text = read_page("CommandCenterPage.vue")
    assert "quick-actions" in text or "Capture" in text
    assert "/capture" in text
    assert "/tasks" in text


def test_command_center_has_section_grouping():
    text = read_page("CommandCenterPage.vue")
    # Should have multiple named sections
    sections = ["Today", "Knowledge", "Operations", "Development"]
    found = sum(1 for s in sections if s in text)
    assert found >= 3, f"CommandCenterPage must have at least 3 named sections, found {found}"


def test_command_center_safe_api_calls():
    text = read_page("CommandCenterPage.vue")
    # All API calls should be wrapped in safe() or try/catch
    assert "safe(" in text or ("try" in text and "catch" in text)
    assert "loadError" in text


def test_command_center_fetches_task_inbox_count():
    text = read_page("CommandCenterPage.vue")
    assert "inboxCount" in text or "inbox" in text


def test_command_center_module_registry_shown():
    text = read_page("CommandCenterPage.vue")
    assert "modules" in text
    assert "Installed modules" in text or "module" in text.lower()


# ---------------------------------------------------------------------------
# BottomNav — correct daily-driver priorities
# ---------------------------------------------------------------------------

def test_bottom_nav_includes_core_daily_items():
    text = read_component("BottomNav.vue")
    assert "capture" in text
    assert "tasks" in text
    assert "command-center" in text


def test_bottom_nav_includes_daily_driver_modules():
    text = read_component("BottomNav.vue")
    assert "capture" in text
    assert "tasks" in text
    assert "'coding-agent'" not in text and '"coding-agent"' not in text


# ---------------------------------------------------------------------------
# Router — all new pages routed
# ---------------------------------------------------------------------------

def test_all_pages_are_routed():
    routes_text = (WEB / "router" / "routes.ts").read_text()
    pages = [
        "CommandCenterPage",
        "CapturePage",
        "TasksPage",
        "StudyCompanionPage",
        "ConnectorsPage",
        "CodingAgentPage",
    ]
    for page in pages:
        assert page in routes_text, f"{page} must be registered in router/routes.ts"


# ---------------------------------------------------------------------------
# Compose — known bad patterns
# ---------------------------------------------------------------------------

def test_compose_no_brittle_qdrant_healthcheck():
    compose = (ROOT / "docker-compose.yml").read_text()
    # qdrant must not have a curl/wget healthcheck that might not exist in the image
    lines = compose.splitlines()
    in_qdrant = False
    in_healthcheck = False
    for line in lines:
        stripped = line.strip()
        if "qdrant:" in stripped:
            in_qdrant = True
        elif re.match(r"^\s{2}\w+:", line) and "qdrant" not in stripped:
            in_qdrant = False
        if in_qdrant and "healthcheck:" in stripped:
            in_healthcheck = True
        if in_qdrant and in_healthcheck and ("curl" in stripped or "wget" in stripped):
            assert False, "qdrant healthcheck must not use curl/wget (brittle upstream container)"


def test_compose_web_build_context_is_monorepo_root():
    compose = (ROOT / "docker-compose.yml").read_text()
    # The web service must build from monorepo root, not apps/web
    web_section_start = compose.find("  web:")
    web_section = compose[web_section_start:web_section_start + 600]
    # context should be "." not "apps/web"
    if "context:" in web_section:
        context_line = [l for l in web_section.splitlines() if "context:" in l]
        if context_line:
            assert "apps/web" not in context_line[0], (
                "web build context must be monorepo root '.', not 'apps/web'"
            )


def test_compose_all_service_ports_unique():
    import yaml
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    seen_ports: dict[str, str] = {}
    for svc_name, svc in compose.get("services", {}).items():
        for port_mapping in svc.get("ports", []):
            host_port = str(port_mapping).split(":")[0].replace("${", "").split(":-")[0]
            # Skip env-var port mappings for uniqueness (they vary by .env)
            if not host_port.startswith("$"):
                if host_port in seen_ports:
                    # Allow same port if same service (shouldn't happen) — just flag duplicates across services
                    assert seen_ports[host_port] == svc_name, (
                        f"Port {host_port} is used by both {seen_ports[host_port]} and {svc_name}"
                    )
                seen_ports[host_port] = svc_name
