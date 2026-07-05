"""Phase C contract tests — Command surface & UX IA.

Locks in: the IA regroup (new surfaces + redirects, old pages still routed),
the Command Center live-query rebuild, palette v2, capture triage, the
Today/Focus surface, the density toggle, and the empty/error-state
enforcement rule from UX_PRODUCT_SPEC.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps/web/src"


def read(rel: str) -> str:
    return (WEB / rel).read_text()


# --- C1: IA regroup -------------------------------------------------------------

def test_new_surfaces_are_routed():
    routes = read("router/routes.ts")
    assert "{ path: '/today', component: DailyPage }" in routes
    assert "{ path: '/continuity', component: ContinuityPage }" in routes
    assert "{ path: '/ops', component: OpsPage }" in routes


def test_canonical_aliases_redirect():
    routes = read("router/routes.ts")
    assert "{ path: '/daily', redirect: '/today' }" in routes
    assert "{ path: '/agents', redirect: '/coding-agent' }" in routes
    assert "{ path: '/twin', redirect: '/digital-twin' }" in routes
    assert "{ path: '/notes', redirect: '/zettelkasten' }" in routes


def test_old_ops_pages_remain_routed_and_embedded_in_continuity():
    routes = read("router/routes.ts")
    continuity = read("pages/ContinuityPage.vue")
    for page in ("BackupRestorePage", "SyncHealthPage", "ConflictResolutionPage", "OfflineQueuePage", "DevicePairingPage"):
        assert page in routes, f"{page} must keep its direct route (contract-pinned)"
        assert page in continuity, f"{page} must be embedded as a Continuity tab"
    # four health tiles
    for tile in ("Last backup", "Sync", "Conflicts", "Offline queue"):
        assert tile in continuity


def test_ia_extends_registry_without_touching_tokens():
    ia = read("design/ia.ts")
    assert "from './tokens'" in ia  # extends, never replaces
    for surface in ("/today", "/projects", "/continuity", "/ops"):
        assert surface in ia


# --- C2: Command Center on live queries -------------------------------------------

def test_command_center_today_strip_is_live():
    text = read("pages/CommandCenterPage.vue")
    assert "daily-state/today" in text          # intention from DailyState
    assert "CAPTURE>" in text                    # inline capture prompt
    assert "api/capture" in text


def test_command_center_attention_chips_navigate_and_are_live():
    text = read("pages/CommandCenterPage.vue")
    for endpoint in ("api/sync/conflicts", "api/coding-agent/jobs", "api/outbox?status=pending_approval", "api/connectors/backup/manifests"):
        assert endpoint in text, f"attention row must query {endpoint}"
    assert "attention" in text
    # chips navigate to their source lists
    assert "/continuity?tab=conflicts" in text
    assert "chip.path" in text


def test_command_center_project_radar_uses_graph():
    text = read("pages/CommandCenterPage.vue")
    assert "api/projects" in text
    assert "graphNeighbors" in text
    assert "belongs_to_project" in text


def test_command_center_keeps_pinned_contract_strings():
    text = read("pages/CommandCenterPage.vue")
    assert 'to="/ambient"' in text
    assert "Installed modules" in text
    assert "safe(" in text and "loadError" in text and "inboxCount" in text


# --- C3: palette v2 -----------------------------------------------------------------

def test_palette_has_actions_and_keyboard_navigation():
    text = read("components/CommandPalette.vue")
    assert "Actions" in text and "Navigate" in text
    assert "New task" in text and "New project" in text
    assert "keydown.down" in text and "keydown.up" in text and "keydown.enter" in text
    assert "graphSearch" in text  # graph section carried over from Phase B


def test_palette_actions_open_creation_forms():
    assert "/tasks?new=1" in read("components/CommandPalette.vue")
    assert "route.query.new === '1'" in read("pages/TasksPage.vue")
    assert "route.query.new === '1'" in read("pages/ProjectsPage.vue")


def test_palette_uses_extended_surface_registry():
    text = read("components/CommandPalette.vue")
    assert "surfaceModules" in text
    assert "from '../design/ia'" in text


# --- C4: capture triage + Today/Focus ------------------------------------------------

def test_capture_service_has_triage_endpoints():
    main = (ROOT / "services/capture-service/app/main.py").read_text()
    assert '"/api/capture/items"' in main
    assert '"/api/capture/items/{item_id}"' in main
    assert "^(inbox|triaged|archived)$" in main


def test_migration_015_adds_capture_status_idempotently():
    sql = (ROOT / "infra/postgres/migrations/015_phase_c_capture_triage.sql").read_text()
    assert "ADD COLUMN IF NOT EXISTS status" in sql
    assert "CREATE INDEX IF NOT EXISTS" in sql


def test_capture_page_has_keyboard_triage():
    text = read("pages/CapturePage.vue")
    for key in ("'j'", "'k'", "'t'", "'n'", "'a'"):
        assert f"case {key}" in text, f"triage key {key} missing"
    assert "api/capture/items" in text
    # keyboard triage must not steal keys from inputs
    assert "'INPUT', 'TEXTAREA'" in text
    # /secretary template + ctrl.enter survive (phase-15 contracts)
    assert "/secretary" in text and "ctrl.enter" in text


def test_today_surface_has_focus_list_and_ritual():
    text = read("pages/DailyPage.vue")
    assert "focusTasks" in text
    assert "isOverdue" in text
    assert "daily-state/open" in text and "daily-state/close" in text


# --- C5: density + enforcement ---------------------------------------------------------

def test_density_toggle_wired():
    assert "density-toggle" in read("pages/SettingsPage.vue")
    prefs = read("services/preferences.ts")
    assert "density-compact" in prefs
    assert "initDensity" in read("App.vue")
    assert "body.density-compact" in read("css/nexus-crt.scss")


PRIMARY_PAGES = [
    "CommandCenterPage.vue",
    "CapturePage.vue",
    "TasksPage.vue",
    "ProjectsPage.vue",
    "DailyPage.vue",
    "ZettelkastenPage.vue",
    "ResearchPage.vue",
    "CodingAgentPage.vue",
    "AutomationPage.vue",
    "DigitalTwinPage.vue",
    "ConnectorsPage.vue",
    "ContinuityPage.vue",
    "SettingsPage.vue",
]


def test_every_primary_surface_handles_errors():
    """UX spec: every primary surface fetches live data and surfaces failures."""
    for page in PRIMARY_PAGES:
        text = read(f"pages/{page}")
        assert "q-banner" in text or "NexusErrorBanner" in text, f"{page} has no error surface"


def test_every_primary_list_surface_has_empty_state():
    """Pages that render lists must render something honest when the list is empty."""
    for page in ("CapturePage.vue", "TasksPage.vue", "ProjectsPage.vue", "ZettelkastenPage.vue", "DailyPage.vue"):
        text = read(f"pages/{page}")
        assert "v-else" in text or "NexusEmptyState" in text, f"{page} has no empty state"
