from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase4_auth_and_packaging_files_exist():
    expected = [
        "infra/postgres/migrations/003_phase_4.sql",
        "apps/mobile/capacitor.config.ts",
        "apps/desktop/src-tauri/tauri.conf.json",
        "apps/web/src/services/auth.ts",
        ".github/workflows/backend-unit.yml",
    ]
    for rel in expected:
        assert (ROOT / rel).exists(), rel
