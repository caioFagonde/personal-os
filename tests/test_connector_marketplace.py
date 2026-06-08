"""Tests for the connector marketplace feature."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


class TestProviderManifestsTS:
    """Validate the TypeScript provider manifests file is well-formed."""

    MANIFESTS_PATH = ROOT / "apps" / "web" / "src" / "providers" / "manifests.ts"

    def test_manifests_file_exists(self):
        assert self.MANIFESTS_PATH.exists(), "manifests.ts must exist"

    def test_exports_provider_manifests(self):
        content = self.MANIFESTS_PATH.read_text()
        assert "PROVIDER_MANIFESTS" in content
        assert "ProviderState" in content
        assert "ProviderManifest" in content
        assert "CostTag" in content

    def test_all_required_providers_present(self):
        content = self.MANIFESTS_PATH.read_text()
        required_ids = [
            "google", "microsoft", "twilio", "ntfy", "tailscale",
            "aws", "azure", "gcp", "github", "claude-code",
            "ollama", "qdrant", "searxng", "n8n", "minio", "tileserver",
        ]
        for pid in required_ids:
            assert f"id: '{pid}'" in content, f"Provider '{pid}' must be in manifests"

    def test_all_provider_states_defined(self):
        content = self.MANIFESTS_PATH.read_text()
        required_states = [
            "not_installed", "needs_config", "malformed_config",
            "ready_to_authorize", "connected", "degraded",
            "dry_run_only", "failed",
        ]
        for state in required_states:
            assert state in content, f"State '{state}' must be defined"

    def test_all_cost_tags_defined(self):
        content = self.MANIFESTS_PATH.read_text()
        required_tags = [
            "local", "private_mesh", "external_provider",
            "free_tier_possible", "paid_external", "verify_pricing",
        ]
        for tag in required_tags:
            assert tag in content, f"Cost tag '{tag}' must be defined"

    def test_cloud_providers_have_safety_notes(self):
        content = self.MANIFESTS_PATH.read_text()
        assert content.count("cloudSafetyNote") >= 3, "AWS, Azure, GCP must have safety notes"
        assert "No automatic paid provisioning" in content
        assert "Dry-run plan only" in content
        assert "Explicit approval" in content

    def test_no_secrets_in_manifests(self):
        content = self.MANIFESTS_PATH.read_text()
        secret_patterns = [
            r"sk-[a-zA-Z0-9]{20,}",
            r"AKIA[A-Z0-9]{16}",
            r"ghp_[a-zA-Z0-9]{30,}",
            r"tskey-auth-[a-zA-Z0-9]+",
        ]
        for pat in secret_patterns:
            assert not re.search(pat, content), f"Secret pattern found in manifests: {pat}"


class TestProviderCardVue:
    """Validate ProviderCard.vue component."""

    CARD_PATH = ROOT / "apps" / "web" / "src" / "components" / "ProviderCard.vue"

    def test_component_exists(self):
        assert self.CARD_PATH.exists(), "ProviderCard.vue must exist"

    def test_has_template_and_script(self):
        content = self.CARD_PATH.read_text()
        assert "<template>" in content
        assert "<script setup lang=\"ts\">" in content

    def test_imports_manifest_types(self):
        content = self.CARD_PATH.read_text()
        assert "ProviderManifest" in content
        assert "ProviderLiveStatus" in content

    def test_displays_state_and_cost(self):
        content = self.CARD_PATH.read_text()
        assert "stateDisplay" in content
        assert "costDisplay" in content
        assert "costTags" in content

    def test_shows_env_config_section(self):
        content = self.CARD_PATH.read_text()
        assert "envRequirements" in content
        assert "q-expansion-item" in content

    def test_shows_cloud_safety_note(self):
        content = self.CARD_PATH.read_text()
        assert "cloudSafetyNote" in content


class TestConnectorsPageVue:
    """Validate the ConnectorsPage.vue marketplace overhaul."""

    PAGE_PATH = ROOT / "apps" / "web" / "src" / "pages" / "ConnectorsPage.vue"

    def test_page_exists(self):
        assert self.PAGE_PATH.exists()

    def test_is_marketplace_page(self):
        content = self.PAGE_PATH.read_text()
        assert "Connector Marketplace" in content
        assert "Marketplace" in content

    def test_uses_provider_card(self):
        content = self.PAGE_PATH.read_text()
        assert "ProviderCard" in content
        assert "import ProviderCard" in content

    def test_has_search_and_filter(self):
        content = self.PAGE_PATH.read_text()
        assert "searchQuery" in content
        assert "filterState" in content
        assert "q-btn-toggle" in content

    def test_has_category_grouping(self):
        content = self.PAGE_PATH.read_text()
        assert "categoryGroups" in content
        assert "section-heading" in content

    def test_has_metrics(self):
        content = self.PAGE_PATH.read_text()
        assert "connectedCount" in content
        assert "needsConfigCount" in content
        assert "MetricCard" in content

    def test_error_handling_no_raw_backend(self):
        content = self.PAGE_PATH.read_text()
        assert "describeConnectorError" in content
        assert "NexusErrorBanner" in content

    def test_keeps_device_code_flow(self):
        content = self.PAGE_PATH.read_text()
        assert "deviceFlow" in content
        assert "pollDeviceFlow" in content
        assert "startDeviceFlow" in content

    def test_keeps_oauth_actions(self):
        content = self.PAGE_PATH.read_text()
        assert "authorize" in content


class TestMarketplaceRoute:
    """Validate routes include /marketplace."""

    ROUTES_PATH = ROOT / "apps" / "web" / "src" / "router" / "routes.ts"

    def test_marketplace_route_exists(self):
        content = self.ROUTES_PATH.read_text()
        assert "/marketplace" in content

    def test_connectors_route_still_exists(self):
        content = self.ROUTES_PATH.read_text()
        assert "/connectors" in content

    def test_both_routes_use_same_component(self):
        content = self.ROUTES_PATH.read_text()
        lines = [l.strip() for l in content.splitlines() if "ConnectorsPage" in l and "path:" in l]
        assert len(lines) >= 2, "Both /connectors and /marketplace should use ConnectorsPage"


class TestBackendMarketplaceEndpoint:
    """Validate the marketplace endpoint is defined in the backend."""

    MAIN_PATH = ROOT / "services" / "connector-service" / "app" / "main.py"

    def test_marketplace_endpoint_exists(self):
        content = self.MAIN_PATH.read_text()
        assert "/api/connectors/marketplace" in content

    def test_marketplace_returns_providers(self):
        content = self.MAIN_PATH.read_text()
        assert "MARKETPLACE_PROVIDERS" in content
        assert '"providers"' in content or "'providers'" in content

    def test_all_providers_in_backend_list(self):
        content = self.MAIN_PATH.read_text()
        required = [
            "google", "microsoft", "twilio", "ntfy", "tailscale",
            "aws", "azure", "gcp", "github", "claude-code",
            "ollama", "qdrant", "searxng", "n8n", "minio", "tileserver",
        ]
        for pid in required:
            assert f'"id": "{pid}"' in content or f'"id":"{pid}"' in content or f"'{pid}'" in content, \
                f"Backend must list provider '{pid}'"

    def test_cloud_providers_flagged(self):
        content = self.MAIN_PATH.read_text()
        assert '"cloud_safety": True' in content or "'cloud_safety': True" in content

    def test_categories_listed(self):
        content = self.MAIN_PATH.read_text()
        assert "categories" in content


class TestProviderStatusDerivation:
    """Test that provider_status_from_env works for all original providers."""

    def test_google_needs_oauth(self):
        from services.connector_service.app.providers import provider_status_from_env
        status = provider_status_from_env({}, "google")
        assert status.configured is False
        assert "needs" in status.status.lower() or "oauth" in status.status.lower()

    def test_google_configured(self):
        from services.connector_service.app.providers import provider_status_from_env
        env = {
            "GOOGLE_CLIENT_ID": "test",
            "GOOGLE_CLIENT_SECRET": "test",
            "GOOGLE_REDIRECT_URI": "http://localhost/callback",
        }
        status = provider_status_from_env(env, "google")
        assert status.configured is True

    def test_ntfy_configured(self):
        from services.connector_service.app.providers import provider_status_from_env
        env = {"NTFY_BASE_URL": "http://ntfy", "NTFY_TOPIC": "test"}
        status = provider_status_from_env(env, "ntfy")
        assert status.configured is True

    def test_twilio_not_configured(self):
        from services.connector_service.app.providers import provider_status_from_env
        status = provider_status_from_env({}, "twilio")
        assert status.configured is False

    def test_tailscale_with_authkey(self):
        from services.connector_service.app.providers import provider_status_from_env
        status = provider_status_from_env({"TAILSCALE_AUTHKEY": "tskey-auth-test"}, "tailscale")
        assert status.configured is True

    def test_unknown_provider_raises(self):
        from services.connector_service.app.providers import provider_status_from_env
        with pytest.raises(ValueError):
            provider_status_from_env({}, "unknown_provider")


class TestConnectorManifestYaml:
    """Validate the connectors module manifest."""

    MANIFEST_PATH = ROOT / "modules" / "connectors" / "manifest.yaml"

    def test_manifest_exists(self):
        assert self.MANIFEST_PATH.exists()

    def test_has_required_fields(self):
        content = self.MANIFEST_PATH.read_text()
        assert "id: connectors" in content
        assert "routes:" in content
        assert "/connectors" in content
