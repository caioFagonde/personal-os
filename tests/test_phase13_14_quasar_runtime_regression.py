from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web"


def test_quasar_router_entrypoint_exists():
    router_index = WEB / "src" / "router" / "index.ts"
    text = router_index.read_text()
    assert "quasar/wrappers" in text
    assert "createRouter" in text
    assert "routes" in text
    assert "VUE_ROUTER_MODE" in text


def test_quasar_boot_file_exports_boot_function():
    boot_file = WEB / "src" / "boot" / "localdb.ts"
    text = boot_file.read_text()
    assert "import { boot } from 'quasar/wrappers'" in text
    assert "export default boot(" in text
    assert "localforage.config" in text


def test_quasar_index_uses_entrypoint_marker_only():
    index = (WEB / "index.html").read_text()
    assert "<!-- quasar:entry-point -->" in index
    assert '<div id="q-app"></div>' not in index
