"""First-usable contract tests — thin-shell mobile + MinIO artifact access.

Locks in the "first usable version" additions:
  * Mobile thin shell: MOBILE_SERVER_URL becomes a live server.url over
    Tailscale so web changes ship without a new APK.
  * MinIO/local artifacts are browsable + streamable through the authenticated
    gateway (never via host-bound presigned URLs a phone can't resolve).
  * A web Files surface wired into routing, IA, and the API client.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps/web/src"


def read(rel: Path) -> str:
    return rel.read_text()


# --- Thin-shell mobile ------------------------------------------------------------

def test_capacitor_thin_shell_maps_server_url_and_host():
    cfg = read(ROOT / "apps/mobile/capacitor.config.ts")
    assert "MOBILE_SERVER_URL" in cfg
    assert "url: serverUrl" in cfg
    assert "new URL(serverUrl).hostname" in cfg
    # Bundled fallback must remain when no server URL is provided.
    assert "webDir: '../web/dist/spa'" in cfg


def test_capacitor_validator_enforces_thin_shell_contract():
    val = read(ROOT / "apps/mobile/scripts/validate-capacitor-config.mjs")
    assert "MOBILE_SERVER_URL" in val
    assert "server.url" in val


# --- MinIO / artifact access ------------------------------------------------------

def test_sync_engine_exposes_list_and_download():
    main = read(ROOT / "services/sync-engine/app/main.py")
    assert '@app.get("/api/attachments")' in main
    assert '@app.get("/api/attachments/{attachment_id}/download")' in main
    # Deleted rows are hidden from listings.
    assert "sync_state <> 'deleted'" in main


def test_download_streams_and_never_presigns_get():
    """Downloads must stream through this service; a presigned GET is host-bound
    to internal minio:9000 and unreachable from a phone over Tailscale."""
    main = read(ROOT / "services/sync-engine/app/main.py")
    assert "StreamingResponse" in main and "FileResponse" in main
    assert "get_object(" in main
    # presigned URLs are only for uploads (PUT), never for the download path.
    assert "HttpMethod=\"PUT\"" in main
    assert 'HttpMethod="GET"' not in main


def test_download_refuses_encrypted_blobs_inline():
    main = read(ROOT / "services/sync-engine/app/main.py")
    assert "attachment_encrypted" in main
    # Inline disposition so PDFs/images render in browser/WebView.
    assert "inline" in main


def test_gateway_forwards_content_disposition():
    gw = read(ROOT / "services/api-gateway/app/main.py")
    assert "content-disposition" in gw.lower()


# --- Web Files surface ------------------------------------------------------------

def test_files_page_exists_with_error_and_empty_state():
    page = read(WEB / "pages/FilesPage.vue")
    assert "listAttachments" in page and "fetchAttachmentObjectUrl" in page
    assert "NexusErrorBanner" in page
    assert "NexusEmptyState" in page or "v-else" in page


def test_files_route_and_ia_registered():
    routes = read(WEB / "router/routes.ts")
    assert "FilesPage" in routes and "/files" in routes
    ia = read(WEB / "design/ia.ts")
    assert "/files" in ia


def test_api_client_has_attachment_helpers():
    api = read(WEB / "services/api.ts")
    assert "listAttachments" in api and "fetchAttachmentObjectUrl" in api
    # Auth header must be attached (a plain <a> tag can't carry the bearer token).
    assert "authHeaders()" in api


# --- One-click Google Drive backup (MinIO + Postgres) -----------------------------

def test_backup_to_drive_chains_snapshot_and_remote():
    script = read(ROOT / "scripts/backup-to-drive.sh")
    assert "scripts/backup-v2.sh" in script
    assert "scripts/backup-remote.sh" in script
    # Never upload an incomplete snapshot.
    assert "manifest.json" in script
    mk = read(ROOT / "Makefile")
    assert "backup-drive" in mk
