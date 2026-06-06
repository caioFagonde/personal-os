from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_phase12_e2e_and_ci_assets_exist():
    required = [
        'playwright.config.ts',
        'e2e/navigation.spec.ts',
        'e2e/offline-conflicts.spec.ts',
        '.github/workflows/phase12-certification-release.yml',
        'scripts/ci/spa-server.py',
    ]
    for rel in required:
        assert (ROOT / rel).exists(), rel
    workflow = read('.github/workflows/phase12-certification-release.yml')
    assert 'browser-e2e' in workflow
    assert 'android-emulator-certification' in workflow
    assert 'restore-drill-certification' in workflow
    assert 'signed-release-artifacts' in workflow


def test_phase12_device_and_release_scripts_are_present_and_executable():
    scripts = [
        'scripts/certify/full-local.sh',
        'scripts/certify/physical-android.sh',
        'scripts/certify/android-emulator.sh',
        'scripts/certify/live-connectors.sh',
        'scripts/release/build-android-signed.sh',
        'scripts/release/build-tauri-signed.sh',
        'scripts/release/verify-release-artifacts.sh',
    ]
    for rel in scripts:
        path = ROOT / rel
        assert path.exists(), rel
        assert path.stat().st_mode & 0o111, rel


def test_phase12_ui_routes_and_navigation_are_wired():
    routes = read('apps/web/src/router/routes.ts')
    tokens = read('apps/web/src/design/tokens.ts')
    assert '/certification' in routes
    assert '/release-center' in routes
    assert 'CertificationPage' in routes
    assert 'ReleaseCenterPage' in routes
    assert 'certification' in tokens
    assert 'release-center' in tokens


def test_phase12_packages_expose_certification_commands():
    root_pkg = read('package.json')
    web_pkg = read('apps/web/package.json')
    assert 'test:e2e' in root_pkg
    assert 'certify:android' in root_pkg
    assert '@playwright/test' in root_pkg
    assert 'preview:ci' in web_pkg


def test_phase12_archive_hygiene_excludes_runtime_artifacts():
    assert not (ROOT / '.env').exists(), '.env'
    gitignore = read('.gitignore')
    assert '.coverage' in gitignore
    assert '__pycache__/' in gitignore
    assert '*.py[cod]' in gitignore
