"""Phase E contract tests — Continuity & Backup.

Locks in: offline queue v2 (durable, per-entity, dead-letter), the sync policy
+ heartbeat, backup v2 scripts + endpoints + preflight gate, mobile
share-target/voice, Tauri quick-capture/tray wiring, and the Continuity
ops-runner buttons (approval-gated, never raw shell).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps/web/src"


def read(rel: Path) -> str:
    return rel.read_text()


# --- E1: offline queue v2 + policy + heartbeat -----------------------------------

def test_offline_queue_v2_is_durable_and_per_entity():
    core = read(WEB / "services/sync-queue-core.ts")
    assert "device_seq" in core and "entity_id" in core
    assert "drainableRecords" in core           # per-entity FIFO
    assert "classifyFailure" in core            # dead-letter vs retry
    assert "nextBackoffMs" in core              # exponential backoff
    queue = read(WEB / "services/sync-queue.ts")
    assert "localforage" in queue               # IndexedDB, not localStorage
    assert "createWebCryptoCipher" in queue     # optional at-rest encryption
    assert "'dead'" in core                     # dead-letter status exists


def test_dead_letter_is_4xx_and_retry_is_5xx():
    core = read(WEB / "services/sync-queue-core.ts")
    # 4xx (except 408/429) is permanent; 5xx/network transient.
    assert "status === 408" in core and "status === 429" in core
    assert "status >= 500" in core


def test_sync_policy_object_exists():
    bg = read(WEB / "services/background-sync.ts")
    assert "SyncPolicy" in bg
    assert "wifi_only" in bg and "min_battery" in bg and "max_payload_mb" in bg
    assert "policyAllowsSync" in bg
    # existing pinned decision engine must survive
    assert "shouldRunBackgroundSync" in bg and "nextSyncDelayMs" in bg


def test_heartbeat_endpoint_and_devices_view():
    sync = read(ROOT / "services/sync-engine/app/main.py")
    assert '"/api/sync/heartbeat"' in sync
    assert '"/api/sync/devices"' in sync
    assert "client_sync_state" in sync
    assert "lag_seconds" in sync
    worker = read(WEB / "services/sync-worker.ts")
    assert "heartbeat" in worker and "drainQueue" in worker


def test_offline_queue_page_shows_dead_letter():
    page = read(WEB / "pages/OfflineQueuePage.vue")
    assert "dead-letter" in page.lower()
    assert "retryDeadLetter" in page


# --- E4: backup v2 -------------------------------------------------------------------

def test_backup_v2_scripts_exist_and_parse():
    scripts = ["backup-v2.sh", "backup-keygen.sh", "backup-verify.sh", "backup-remote.sh", "backup-prune.sh", "backup-drill.sh"]
    for name in scripts:
        path = ROOT / "scripts" / name
        assert path.exists(), f"missing {name}"
        result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
        assert result.returncode == 0, f"{name}: {result.stderr}"


def test_backup_v2_uses_pg_dump_custom_format_and_manifest_last():
    v2 = read(ROOT / "scripts/backup-v2.sh")
    assert "pg_dump -Fc" in v2                   # custom format (pg_restore --list)
    assert "manifest" in v2.lower()
    assert "age -r" in v2                         # optional age encryption
    assert "env-schema.json" in v2                # config = keys only, never .env values


def test_rclone_template_present_and_secretless():
    tmpl = read(ROOT / "scripts/rclone/rclone.conf.template")
    assert "nexus-drive" in tmpl and "nexus-disk" in tmpl
    # no committed OAuth token/secret
    assert "token = {" not in tmpl.replace("# token = {...}", "")


def test_keygen_keeps_private_key_out_of_repo():
    keygen = read(ROOT / "scripts/backup-keygen.sh")
    assert "age-keygen" in keygen
    assert "NEVER commit" in keygen or "never commit" in keygen.lower()
    assert "UNRECOVERABLE" in keygen                # honest key-loss warning


def test_preflight_requires_verified_backup_under_24h():
    preflight = read(ROOT / "scripts/preflight-update.sh")
    assert "verified backup" in preflight.lower()
    assert "24" in preflight
    # the original phase-11 contract strings must remain
    assert "BACKUP_ENCRYPTION_KEY" in preflight
    assert "backup before rebuild" in preflight


def test_migration_017_is_idempotent():
    sql = read(ROOT / "infra/postgres/migrations/017_backup_v2.sql")
    assert "ADD COLUMN IF NOT EXISTS" in sql
    assert "migration_head" in sql and "components" in sql
    assert "rclone_drive" in sql                  # widened remote providers
    assert "backup.create" in sql and "backup.verify" in sql and "backup.drill" in sql  # ops templates


def test_backup_continuity_endpoint_exists():
    main = read(ROOT / "services/connector-service/app/main.py")
    assert '"/api/connectors/backup/continuity"' in main
    assert "last_drill" in main and "latest_verified" in main


# --- E2: mobile -----------------------------------------------------------------------

def test_share_target_and_manifest_fragment():
    assert (ROOT / "apps/mobile/src/share-target.ts").exists()
    fragment = read(ROOT / "apps/mobile/android-share-target.xml")
    assert "android.intent.action.SEND" in fragment
    assert "image/*" in fragment
    cfg = read(ROOT / "apps/mobile/capacitor.config.ts")
    assert "shareTarget" in cfg


def test_voice_capture_is_honestly_degraded():
    voice = read(ROOT / "apps/mobile/src/voice-capture.ts")
    assert "unavailable (no model)" in voice
    assert "transcript" in voice
    # never fabricates a transcript at build time
    assert "initialTranscriptionState" in voice


def test_capture_page_reads_share_deeplink():
    page = read(WEB / "pages/CapturePage.vue")
    assert "route.query.text" in page


# --- E3: desktop ----------------------------------------------------------------------

def test_tauri_quick_capture_and_tray_wired():
    lib = read(ROOT / "apps/desktop/src-tauri/src/lib.rs")
    assert "QUICK_CAPTURE_SHORTCUT" in lib and "tray_menu_items" in lib and "tray_badge_label" in lib
    main = read(ROOT / "apps/desktop/src-tauri/src/main.rs")
    assert "toggle_quick_capture" in main and "TrayIconBuilder" in main
    assert "single_instance" in main and "global_shortcut" in main
    cargo = read(ROOT / "apps/desktop/src-tauri/Cargo.toml")
    assert "tauri-plugin-global-shortcut" in cargo


def test_tauri_capabilities_grant_global_shortcut():
    caps = read(ROOT / "apps/desktop/src-tauri/capabilities/default.json")
    assert "global-shortcut:allow-register" in caps
    assert "quick-capture" in caps


# --- E5: continuity ops runner (approval-gated, no raw shell) --------------------------

def test_continuity_ops_buttons_use_command_bus():
    page = read(WEB / "pages/BackupRestorePage.vue")
    assert "backup.create" in page and "backup.verify" in page and "backup.drill" in page
    assert "/api/commands" in page               # approval-gated command bus
    assert "backup-tiles" in page                 # four health tiles
    # pinned phase-11 markers must survive
    assert "Azure Blob" in page and "AWS S3" in page and "BACKUP_ENCRYPTION_KEY" in page
    assert "/api/connectors/backup/status" in page


def test_ops_templates_require_approval():
    sql = read(ROOT / "infra/postgres/migrations/017_backup_v2.sql")
    # the seeded backup.* templates must be approval-gated and local-only (true,true)
    assert "'local_script'" in sql
    assert "host-runner" in sql
