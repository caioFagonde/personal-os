"""
V1 productization regression tests.
Verifies icon configuration, dark-theme CSS, design system components,
and page-level visual contracts.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web" / "src"
CSS = (WEB / "css" / "app.scss").read_text()
QUASAR_CONFIG = (ROOT / "apps" / "web" / "quasar.config.ts").read_text()


def read_page(name: str) -> str:
    return (WEB / "pages" / name).read_text()


def read_component(name: str) -> str:
    return (WEB / "components" / name).read_text()


# ---------------------------------------------------------------------------
# Phase 1: Icon configuration
# ---------------------------------------------------------------------------

def test_quasar_icon_set_configured():
    assert "iconSet: 'mdi-v7'" in QUASAR_CONFIG or 'iconSet: "mdi-v7"' in QUASAR_CONFIG, (
        "quasar.config.ts must set framework.iconSet to 'mdi-v7' to prevent literal text icons"
    )


def test_quasar_mdi_extras_loaded():
    assert "mdi-v7" in QUASAR_CONFIG, "quasar.config.ts must load mdi-v7 extras"


# ---------------------------------------------------------------------------
# Phase 1: Dark-theme CSS contracts
# ---------------------------------------------------------------------------

def test_overflow_x_hidden():
    assert "overflow-x: hidden" in CSS or "overflow-x:hidden" in CSS, (
        "html/body must have overflow-x: hidden to prevent horizontal scrollbars"
    )


def test_hero_h1_has_font_size_clamp():
    assert "clamp(" in CSS, "hero h1 must use clamp() for responsive font sizing"


def test_form_field_dark_background():
    assert "q-field__control" in CSS, "q-field__control must be styled for dark theme"
    assert "rgba(15, 23, 42" in CSS, "Form field backgrounds must use dark rgba"


def test_stepper_dark_theme():
    assert ".q-stepper" in CSS, "q-stepper must have dark-theme styles"
    assert ".q-stepper__tab" in CSS


def test_expansion_item_dark_theme():
    assert ".q-expansion-item" in CSS, "q-expansion-item must have dark-theme styles"


def test_toggle_dark_theme():
    assert ".q-toggle" in CSS, "q-toggle must have dark-theme styles"


def test_tabs_dark_theme():
    assert ".q-tab--active" in CSS, "q-tab--active must have dark-theme styles"


def test_chip_dark_theme():
    assert ".q-chip" in CSS, "q-chip must have dark-theme styles"


def test_focus_visible_outlines():
    assert ":focus-visible" in CSS, "focus-visible outlines must be defined"


def test_separator_dark_theme():
    assert ".q-separator" in CSS, "q-separator must have dark-theme styles"


def test_select_dropdown_dark_theme():
    assert ".q-select" in CSS, "q-select must have dark-theme styles"


def test_banner_dark_theme():
    assert ".q-banner" in CSS, "q-banner must have dark-theme styles"


# ---------------------------------------------------------------------------
# Phase 2: Design system components exist
# ---------------------------------------------------------------------------

def test_nexus_page_hero_component_exists():
    text = read_component("NexusPageHero.vue")
    assert "hero-panel" in text
    assert "eyebrow" in text
    assert "title" in text


def test_nexus_panel_component_exists():
    text = read_component("NexusPanel.vue")
    assert "nexus-panel" in text


def test_nexus_status_badge_component_exists():
    text = read_component("NexusStatusBadge.vue")
    assert "q-badge" in text
    assert "positive" in text
    assert "negative" in text


def test_nexus_empty_state_component_exists():
    text = read_component("NexusEmptyState.vue")
    assert "nexus-empty" in text


def test_nexus_module_card_component_exists():
    text = read_component("NexusModuleCard.vue")
    assert "glass-card" in text
    assert "module-card-item" in text


# ---------------------------------------------------------------------------
# Phase 5: All pages use NexusPageHero or hero-panel
# ---------------------------------------------------------------------------

PAGES_WITH_HERO = [
    "CommandCenterPage.vue",
    "CapturePage.vue",
    "TasksPage.vue",
    "StudyCompanionPage.vue",
    "CodingAgentPage.vue",
    "ConnectorsPage.vue",
    "ZettelkastenPage.vue",
    "StudyPage.vue",
    "GeospatialPage.vue",
    "ARMemoryPage.vue",
    "AutomationPage.vue",
    "ResearchPage.vue",
    "SyncPage.vue",
    "SyncHealthPage.vue",
    "OfflineQueuePage.vue",
    "ModelRuntimePage.vue",
    "LiveStackPage.vue",
    "ReleaseCenterPage.vue",
    "ConflictResolutionPage.vue",
    "BackupRestorePage.vue",
    "DevicePairingPage.vue",
    "ConnectorWorkerPage.vue",
    "CertificationPage.vue",
    "OnboardingPage.vue",
    "InitialVersionReadinessPage.vue",
]


def test_all_pages_use_nexus_page_hero():
    for page_name in PAGES_WITH_HERO:
        text = read_page(page_name)
        assert "NexusPageHero" in text or "hero-panel" in text, (
            f"{page_name} must use NexusPageHero or hero-panel"
        )


def test_digital_twin_hero_not_oversized():
    text = read_page("DigitalTwinPage.vue")
    match = re.search(r"clamp\(\s*\d+px", text)
    if match:
        min_size = int(re.search(r"(\d+)", match.group()).group())
        assert min_size <= 34, f"DigitalTwinPage min font-size {min_size}px should be <= 34px"


def test_module_page_uses_nexus_page_hero():
    text = read_page("ModulePage.vue")
    assert "NexusPageHero" in text


def test_onboarding_uses_glass_card():
    text = read_page("OnboardingPage.vue")
    assert "glass-card" in text, "OnboardingPage stepper must be in a glass-card"
    assert "NexusPageHero" in text


# ---------------------------------------------------------------------------
# Phase 6: Settings page
# ---------------------------------------------------------------------------

def test_settings_page_exists():
    text = read_page("SettingsPage.vue")
    assert "NexusPageHero" in text
    assert "Settings" in text


def test_settings_page_has_validation():
    text = read_page("SettingsPage.vue")
    assert ":rules" in text, "Settings must have input validation rules"
    assert "E.164" in text, "Settings must validate phone number format"


def test_settings_page_has_save():
    text = read_page("SettingsPage.vue")
    assert "localStorage" in text, "Settings must persist to localStorage"
    assert "save" in text


def test_settings_page_has_service_health_check():
    text = read_page("SettingsPage.vue")
    assert "serviceStatus" in text or "checkServices" in text


def test_settings_route_exists():
    routes_text = (WEB / "router" / "routes.ts").read_text()
    assert "SettingsPage" in routes_text
    assert "/settings" in routes_text


def test_settings_in_navigation():
    tokens = (WEB / "design" / "tokens.ts").read_text()
    assert "'settings'" in tokens or '"settings"' in tokens


# ---------------------------------------------------------------------------
# Phase 11: API error normalization
# ---------------------------------------------------------------------------

def test_api_gateway_has_global_exception_handler():
    text = (ROOT / "services" / "api-gateway" / "app" / "main.py").read_text()
    assert "exception_handler" in text
    assert '"error"' in text or "'error'" in text


def test_api_gateway_proxy_handles_connection_errors():
    text = (ROOT / "services" / "api-gateway" / "app" / "main.py").read_text()
    assert "ConnectError" in text
    assert "service_unavailable" in text


def test_connector_service_has_error_handler():
    text = (ROOT / "services" / "connector-service" / "app" / "main.py").read_text()
    assert "exception_handler" in text


# ---------------------------------------------------------------------------
# Phase 13: Shell and layout contracts
# ---------------------------------------------------------------------------

def test_app_has_settings_button():
    text = (WEB / "App.vue").read_text()
    assert "/settings" in text, "App.vue must have a settings button"


def test_app_has_command_palette():
    text = (WEB / "App.vue").read_text()
    assert "CommandPalette" in text


def test_app_has_system_status_ribbon():
    text = (WEB / "App.vue").read_text()
    assert "SystemStatusRibbon" in text


def test_app_has_bottom_nav():
    text = (WEB / "App.vue").read_text()
    assert "BottomNav" in text


def test_scrollbar_styling():
    assert "::-webkit-scrollbar" in CSS


def test_tooltip_dark_theme():
    assert ".q-tooltip" in CSS
