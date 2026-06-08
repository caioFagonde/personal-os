# Scout Report: Portable Capsule Mode and Safe Install/Update Workflow

**Task:** portable-capsule-installer - Portable USB/capsule mode and safe install/update workflow
**Date:** 2026-06-08
**Status:** Ready for implementation

---

## Executive Summary

Personal OS currently has a functional single-machine bootstrap workflow (`scripts/bootstrap.sh`) but lacks portable/capsule mode support for USB-based deployment and safe, attestable install/update procedures. The bootstrap script hardcodes data directories to `./data/*`, relies on Docker named volumes for stateful services, and has no mechanism to:

1. Configure runtime directories via environment variables (for USB portability)
2. Validate preflight requirements (Docker, Tailscale, ADB, pnpm, Python version, available disk space)
3. Create audit-trail backups before updates (preflight exists but is incomplete)
4. Verify restore/rollback reliability before shipping
5. Document portable mode constraints and setup for end users

**Gap:** An operator cannot currently install Personal OS to a USB drive or airgapped portable device with confidence that:
- No host credentials are persisted after unplug
- The install is reproducible and auditable
- Updates can be safely rolled back
- The installation validates all required tools and disk space before committing

---

## Relevant Files

### Bootstrap and Installation

- `scripts/bootstrap.sh` — primary installation script; hardcodes data dirs to `./data/`; validates git, docker, pnpm, python3; optional adb, tailscale warnings
- `scripts/bootstrap.ps1` — Windows PowerShell version; minimal feature parity with bash
- `scripts/doctor.sh` — diagnostic tool; checks tool versions and `.env` presence
- `scripts/doctor-full.sh` — extended diagnostics (exists but content unknown)
- `scripts/check-secrets.sh` — regex-based local secret detector; guards against committed credentials
- `.env.example` — configuration template (read-protected by design)

### Backup, Update, and Recovery

- `scripts/backup.sh` — creates postgres dump and tar of data/artifacts/exports/generated
- `scripts/update.sh` — rebuilds Docker images and restarts services with ntfy notification; records git refs for rollback
- `scripts/preflight-update.sh` — validates BACKUP_ENCRYPTION_KEY, calls backup via curl, skips on missing key
- `scripts/rollback-last-update.sh` — reads recorded git refs and checks out previous commit; requires clean working tree
- `scripts/restore.sh` — accepts postgres dump file; manual confirmation required

### Docker Compose and Service Configuration

- `docker-compose.yml` — defines all services with profiles; uses named volumes (postgres_data, minio_data, etc.), mount points to `./data/`, `./backups/`, `./workspace/`
- Services affected by data location:
  - `postgres`: `postgres_data:/var/lib/postgresql/data`
  - `minio`: `minio_data:/data`
  - `connector-service`: `./backups:/workspace/backups`
  - `sync-engine`: environmental MINIO config
  - `research-service`: `./data/research:/data/research`
  - `model-runtime`: environmental MINIO config
  - `coding-agent-service`: `.:/workspace` and `./.agent-worktrees:/workspace/.agent-worktrees`

### Environment and Configuration

- `.env` — generated at runtime; forbidden path (secrets protection)
- `scripts/generate-env.py` — creates `.env` with generated passwords (assumed to exist but not readable)
- `Makefile` (justfile) — defines `install`, `doctor`, `up`, `down`, `backup`, `restore`, `nuke` targets

### Documentation

- `docs/install.md` — basic install steps; no portable or capsule mode guidance
- `docs/backup.md` — documents encrypted backups with Fernet key; cloud provider options (AWS S3, Azure Blob)
- `docs/security.md` — lists non-negotiables: no committed .env, no unauthenticated remote shell, audit logs
- `README.md` — references Phase 1-3 implementation; mentions one-script install but no portability details

### Tests and Validation

- `scripts/restore-drill.sh` — integration test for backup/restore; inserts sample data and exports backup manifest
- `e2e/` — Playwright tests (presence confirmed)
- `tests/` — pytest backend tests (presence confirmed)

---

## Current State Assessment

### What Works

1. **Core bootstrap flow**: `bootstrap.sh` creates `.env`, runtime directories, starts Docker Compose, runs migrations, performs auth smoke test, optionally deploys mobile/desktop.
2. **Secret generation**: `scripts/generate-env.py` creates `.env.example` → `.env` with random passwords; no hardcoded secrets in repo.
3. **Preflight dependency checks**: Validates git, docker, docker-compose, warns on optional tools (pnpm, python3, adb, tailscale).
4. **Backup workflow**: `backup.sh` creates postgres dump and runtime tar; timestamps recorded; encryption key required by `preflight-update.sh`.
5. **Rollback metadata**: `update.sh` records before/after git refs in `tmp/update/last-update.refs`; `rollback-last-update.sh` reads and checks out.
6. **Health checks**: Bootstrap runs curl tests on API gateway, sync engine, command bus, module service; reports pass/warn/fail.
7. **Multimode bootstrap**: `--full`, `--apps`, `--core` profiles allow incremental service startup.
8. **Interactive auth**: Optional Tailscale, ADB, and OAuth handoff after bootstrap.
9. **Restore drill**: Integration test verifies backup/restore path creates sample data, exports manifest, validates query.
10. **Platform detection**: detect capability in web shell; mobile-specific considerations exist.

### What's Missing

1. **No portable mode documentation**: Docs don't explain USB/capsule deployment constraints, portable data directory config, or cleanup procedures.
2. **Runtime directories hardcoded**: Bootstrap creates `./data/{postgres,postgis,qdrant,minio,ollama,nats,ntfy,tailscale,maps,research}` relative to script location; no env var override (e.g., `PERSONAL_OS_DATA_DIR`).
3. **Docker volume conflicts on remount**: Named volumes (`postgres_data`, `minio_data`, etc.) are tied to the Docker daemon and hostname; USB drive moved between hosts causes stale volume references.
4. **No comprehensive preflight validation**: Missing checks for:
   - Required disk space (≥10 GB estimated for full stack)
   - Docker API version compatibility
   - USB drive I/O speed / filesystem type (ext4, NTFS, APFS)
   - Python 3.10+ (only checks for python3 binary)
   - pnpm version (only checks existence)
   - Available RAM for Docker (≥4 GB recommended)
   - Port conflicts (8080, 8081, 8082, etc.)
5. **Backup encryption key not generated**: `BACKUP_ENCRYPTION_KEY` must be pre-set or `preflight-update.sh` fails; no documentation on generating or rotating it.
6. **Update flow doesn't validate rollback path**: `update.sh` records git refs but doesn't verify that the previous commit builds cleanly or that rollback will succeed.
7. **No restore validation before commit**: `restore.sh` requires manual confirmation but doesn't validate dump integrity or schema compatibility before importing.
8. **Credential persistence after unplug**: If containers are stopped but volumes remain mounted on host, secrets in Docker named volumes are not automatically cleaned up; no documented cleanup script.
9. **No portable-mode health check**: Bootstrap doesn't validate that relocated/portable setup functions end-to-end (e.g., after moving USB to different host).
10. **Windows bootstrap incomplete**: `bootstrap.ps1` is minimal; doesn't match feature parity of bash version; no equivalent for update, restore, rollback.
11. **No airgapped/offline install guidance**: Bootstrap requires internet to pull Docker images and pnpm dependencies; no documented layered image export or cache mechanism.
12. **Restore drill only tests core + apps**: Doesn't exercise full profile or verify all service migrations idempotent.
13. **No version pinning for tools**: Bash uses `command -v` without version checks; breaking API changes in docker, git, etc. could silently cause failures.

---

## Implementation Points

### 1. Portable Mode Configuration (High Priority)

**Objective:** Allow runtime directories to be relocatable (USB, network mount, custom path).

**Changes:**

1. **New environment variable**: `PERSONAL_OS_DATA_DIR` (defaults to `./data`)
   - If set, all persistent directories route to `${PERSONAL_OS_DATA_DIR}/{postgres,minio,qdrant,nats,ntfy,tailscale,maps,research,ollama}`
   - Example: `PERSONAL_OS_DATA_DIR=/mnt/usb/personal-os-data`

2. **Modify docker-compose.yml**
   - Replace hardcoded paths with env var templating
   - Example: `- ${PERSONAL_OS_DATA_DIR:-./data}/postgres:/var/lib/postgresql/data`
   - Test with `docker compose config` to ensure interpolation works

3. **Update bootstrap.sh**
   - Add flag: `--data-dir /path/to/data` or read from env var
   - Create target directory if missing
   - Document recommendation: use ext4/NTFS with ≥10 GB free
   - Validate directory is writable before starting services

4. **Update backup/restore scripts**
   - Accept `--data-dir` flag or read from env var
   - Adjust backup paths accordingly
   - Document in-place restore (restore to same portable device) vs. migrate to new device

5. **Documentation: `docs/portable-mode.md`**
   - USB preparation (formatting, min size, filesystem)
   - Installation with portable data dir
   - Sync and mobile connection over Tailscale
   - Cleanup and credential removal procedures

### 2. Comprehensive Preflight Validation (High Priority)

**Objective:** Fail-fast with actionable diagnostics before committing to install.

**Create: `scripts/preflight.sh`**

```bash
./scripts/preflight.sh [--data-dir PATH] [--profile core|apps|full]
```

**Validations:**

- **Docker and CLI**
  - `docker` ≥ 20.10.0
  - `docker compose` ≥ 2.0.0
  - `docker ps` works (daemon access)

- **Required Tools**
  - `git` ≥ 2.30
  - `curl` (for health checks and ntfy)
  - `python3` ≥ 3.10

- **Optional Tools (warn, don't fail)**
  - `pnpm` (for app builds)
  - `adb` (for mobile deploy)
  - `tailscale` (for mesh networking)
  - `cargo` / `rustc` (for desktop builds)

- **System Resources**
  - Available RAM ≥ 4 GB (check `/proc/meminfo` or `vm_stat`)
  - Available disk space ≥ 10 GB for `$PERSONAL_OS_DATA_DIR`
  - Disk I/O speed test (optional: dd throughput benchmark)

- **Port Availability**
  - Core ports: 8080, 8081, 8082, 8083 (free and not in TIME_WAIT)
  - Optional ports: 5678 (n8n), 6333 (qdrant), 9010 (minio), 11434 (ollama)

- **Filesystem Constraints**
  - If `--data-dir` on USB: warn if NTFS (slow) or FAT32 (no symlinks)
  - Verify directory is not read-only

- **Environment Pre-Check**
  - Warn if `.env` exists but looks stale (check `COMPOSE_PROJECT_NAME`, API ports)
  - Warn if `data/` directory exists but is empty (possible partial migration)

**Output:**
```
✓ docker 24.0.6
✗ pnpm not found (app builds will be skipped)
⚠ Available RAM: 3.8 GB (recommended ≥4 GB)
✓ Disk available: 250 GB at /mnt/usb
→ Ready to bootstrap
```

**Error Exit Codes:**
- 1: Missing required dependency
- 2: Insufficient resources
- 3: Port/directory conflict

### 3. Safe Update Flow with Rollback Validation (High Priority)

**Objective:** Verify rollback safety before update; create audit trail.

**Enhance: `scripts/preflight-update.sh`**

1. Validate backup encryption key is set and non-empty
2. Validate BACKUP_ENCRYPTION_KEY length (Fernet keys ≥44 chars)
3. Check git working tree is clean
4. Test backup export endpoint (`/api/connectors/backup/export`)
5. **New:** Verify rollback metadata exists and is readable
6. **New:** Dry-run Docker build for previous commit to ensure rollback path is valid
7. Log preflight results with timestamp to `logs/update-preflight-YYYYmmdd-HHMMSS.log`

**Update: `scripts/update.sh`**

1. Call `preflight-update.sh --execute` (blocking if --dry-run)
2. Create timestamped backup directory: `backups/update-YYYYmmdd-HHMMSS/`
3. Copy backup artifact, migrations, and current docker-compose.yml to backup dir
4. Record rollback metadata: before commit, after commit, backup path
5. After successful restart, write summary: "Update YYYYmmdd-HHMMSS: commit A → B completed"
6. If update fails after docker compose up, automatically trigger rollback prompt:
   ```
   Update failed. Rollback available:
   ./scripts/rollback-last-update.sh --execute
   ```

### 4. Restore Drill and Validation (Medium Priority)

**Objective:** Ensure backup/restore path is reliable and auditable before first use.

**Enhance: `scripts/restore-drill.sh`**

1. Accept optional `--profile full` to exercise all services
2. Run full migration suite (not just sample inserts)
3. Verify all service health endpoints respond (not just postgres)
4. Export and import encrypted backup manifest (if key is set)
5. Validate data integrity after restore (row counts, checksums)
6. Log results to `logs/restore-drill-YYYYmmdd-HHMMSS.log`

**New: `scripts/validate-restore.sh`**

```bash
./scripts/validate-restore.sh backups/postgres-YYYYmmdd-HHMMSS.sql [--dry-run]
```

- Validates dump file integrity (check if gzip compressed, readable)
- Counts tables and rows in dump
- Estimates restore time
- Checks for deprecated SQL patterns
- Reports without executing (--dry-run mode)

### 5. Credential Cleanup and Portable Safety (Medium Priority)

**New: `scripts/cleanup-portable.sh`**

```bash
./scripts/cleanup-portable.sh [--data-dir PATH]
```

**Actions:**

1. Stop all containers
2. Remove Docker named volumes (e.g., `postgres_data`, `minio_data`)
   ```bash
   docker compose --env-file .env down -v
   ```
3. Shred or overwrite `.env` file (if flag: `--shred-env`)
4. Optionally clear `data/` directories
5. Verify no running containers or dangling volumes
6. Report: "Portable device cleaned for safe unplug"

**Documentation:** Recommend running before unplugging USB from security-sensitive environment.

### 6. Documentation and User Guidance (Medium Priority)

**Create: `docs/portable-mode.md`**

- USB preparation (min size, filesystem, speed)
- One-line bootstrap for portable (e.g., `PERSONAL_OS_DATA_DIR=/mnt/usb ./scripts/bootstrap.sh`)
- Preflight validation walkthrough
- Backup/restore procedures
- Cleanup for safe unplug
- Migrating portable install to new USB
- Troubleshooting: "after moving USB, services don't start" (stale volume refs)

**Update: `docs/install.md`**

- Link to portable mode guide
- Add prerequisite section with `./scripts/preflight.sh` command

**Create: `docs/update-safety.md`**

- Update workflow with preflight validation
- Rollback procedures
- What to do if rollback fails
- Backup encryption key management

---

## Risks and Conflicts

### Risk 1: Volume Name Conflicts Across Multiple Installs

**Scenario:** Operator installs Personal OS to two USB drives on same host. Docker named volumes collide because both use `postgres_data`, `minio_data`, etc.

**Mitigation:**
- Use `COMPOSE_PROJECT_NAME` to isolate volumes: e.g., `COMPOSE_PROJECT_NAME=personal_os_usb_drive_1`
- Document in `docs/portable-mode.md`: "Set unique `COMPOSE_PROJECT_NAME` if running multiple portable instances on same host"
- Update `docker-compose.yml` top-level `name:` to use env var

### Risk 2: Filesystem Type Limitations

**Scenario:** Operator formats USB as FAT32. Symlinks fail; docker volumes break.

**Mitigation:**
- Preflight script warns if `--data-dir` is on FAT32
- Documentation recommends ext4 (Linux), NTFS (Windows), APFS (macOS)
- Provide USB format instructions for common tools

### Risk 3: Docker Daemon on Different Host

**Scenario:** USB move to new machine. Docker daemon doesn't have volume records. Containers fail to mount.

**Mitigation:**
- Preflight validation checks for stale volume references
- If volumes missing, offer to recreate them: `docker volume create postgres_data`
- Document in troubleshooting: "Services fail to start on new host—run: `./scripts/doctor.sh && docker compose --env-file .env up -d`"

### Risk 4: Backup Encryption Key Loss

**Scenario:** Operator loses `BACKUP_ENCRYPTION_KEY`. Backups unrecoverable.

**Mitigation:**
- Warn during bootstrap if key not set: "BACKUP_ENCRYPTION_KEY not configured; backups will fail on update"
- Provide `scripts/generate-backup-key.sh` to create and securely store Fernet key
- Documentation: "Store backup key separately (e.g., password manager) and restore to .env before update"

### Risk 5: Slow USB Causes Health Check Timeout

**Scenario:** USB 2.0 drive; postgres startup takes >30s. Health check times out; containers restart loop.

**Mitigation:**
- Increase health check `start_period` for portable deployments (e.g., `start_period: 30s` vs. `start_period: 10s`)
- Or provide `docker-compose.portable.yml` override with adjusted timeouts
- Document: "Use USB 3.0 or faster; expect slower startup times on older USB drives"

### Risk 6: Partial Update Leaves System Broken

**Scenario:** `docker compose build` fails mid-stream. Services mix old and new images. System unstable.

**Mitigation:**
- `preflight-update.sh` validates that previous commit builds cleanly (dry-run Docker build)
- `update.sh` backs up before building
- If `docker compose up` fails, auto-suggest rollback
- Logs all steps to audit trail

### Risk 7: Data Corruption on Force Unplug

**Scenario:** User unplugs USB while containers running. Database in middle of write.

**Mitigation:**
- Documentation: "Always stop services before unplugging: `./scripts/down.sh` or `make down`"
- Optional: Create `scripts/safe-eject.sh` that stops services, flushes volumes, and reports ready
- Postgres WAL and fsync settings should protect against minor crashes, but data safety is operator's responsibility

### Risk 8: Rollback Fails Due to Breaking Migration

**Scenario:** Upgrade includes new migration. Rollback checks out old code but database still has new schema. Services fail.

**Mitigation:**
- Preflight validation runs `rollback-last-update.sh --dry-run` to verify git checkout works
- Before rolling back, operator should restore database from backup
- Document: "If rollback fails after schema change, use: `./scripts/restore.sh backups/postgres-YYYYMMDD-HHMMSS.sql`"
- Consider `rollback-last-update.sh` to automatically trigger restore if migrations changed

### Risk 9: Offline/Airgapped Install Not Supported

**Scenario:** Operator wants to install on machine without internet. Image pulls and pnpm installs fail.

**Mitigation:**
- Document: "Internet required for first install (image pull and pnpm dependencies)"
- Optional: Create `scripts/export-images.sh` to save Docker images as tar for transfer to airgapped machine
- For Phase 2: Implement offline image caching / layer export mechanism

### Risk 10: Windows Path Separators Break Scripts

**Scenario:** Windows operators use `bootstrap.ps1` but environment vars use `/` path separators. `PERSONAL_OS_DATA_DIR` set to Windows path.

**Mitigation:**
- Bootstrap.ps1 normalizes paths: `$DataDir -replace '\\', '/'`
- Or use `Convert-Path` to resolve to UNC path
- Test bootstrap.ps1 on Windows with portable data dir

---

## Tests to Run

### Unit/Script Tests

```bash
# Validate bash syntax
bash -n scripts/bootstrap.sh
bash -n scripts/preflight.sh
bash -n scripts/update.sh
bash -n scripts/preflight-update.sh
bash -n scripts/rollback-last-update.sh
bash -n scripts/cleanup-portable.sh
bash -n scripts/validate-restore.sh

# Check for secrets in scripts
./scripts/check-secrets.sh

# Validate docker-compose structure
docker compose --env-file .env.example --profile full config > /tmp/personal-os-compose-check.yml
```

### Integration Tests

1. **Preflight validation**
   ```bash
   ./scripts/preflight.sh --profile core
   # Verify output includes all required tools, resource checks, port availability
   ```

2. **Portable bootstrap to custom dir**
   ```bash
   mkdir /tmp/test-portable-data
   PERSONAL_OS_DATA_DIR=/tmp/test-portable-data ./scripts/bootstrap.sh --core
   # Verify data directories created at /tmp/test-portable-data/{postgres,minio,etc}
   # Verify services start and health checks pass
   ```

3. **Backup before update**
   ```bash
   ./scripts/preflight-update.sh --dry-run
   # Verify encryption key check, backup export test, rollback metadata validation
   ```

4. **Restore drill with full profile**
   ```bash
   ./scripts/restore-drill.sh --profile full
   # Verify all services boot, sample data inserted, backup exported, data queryable
   ```

5. **Cleanup portable**
   ```bash
   ./scripts/cleanup-portable.sh --data-dir /tmp/test-portable-data
   # Verify containers stopped, volumes removed, .env cleared (if --shred-env)
   ```

6. **Rollback safety check**
   ```bash
   ./scripts/update.sh --dry-run
   # Verify previous commit builds, rollback metadata logged
   ```

### End-to-End Tests

```bash
# E2E: Install, update, restore, rollback
pytest tests/test_portable_install.py -q

# E2E: USB migration scenario (move data dir between mounts)
pytest tests/test_portable_migration.py -q
```

### Manual Testing Checklist

- [ ] `./scripts/preflight.sh` on machine with missing optional tool (e.g., no adb) — warn, don't fail
- [ ] `./scripts/preflight.sh` on machine with insufficient RAM — fail with actionable message
- [ ] `./scripts/preflight.sh --data-dir /mnt/usb` where USB has 50 GB available — pass
- [ ] `PERSONAL_OS_DATA_DIR=/mnt/usb ./scripts/bootstrap.sh --core` — data created at `/mnt/usb/postgres`, etc.
- [ ] Bootstrap on machine 1; backup; move data dir USB to machine 2; bootstrap again — services start and data persists
- [ ] `./scripts/update.sh --dry-run` — shows what would be built, backup location, rollback metadata
- [ ] `./scripts/update.sh` → fails after docker compose up → manual rollback → services restore to previous state
- [ ] `./scripts/restore-drill.sh` on full profile — all services boot, sample data inserted, backup manifest exported
- [ ] `./scripts/cleanup-portable.sh --data-dir /tmp/test` → containers stopped, volumes removed, safe to unplug message printed
- [ ] Bootstrap Windows with `bootstrap.ps1 -DataDir "C:\Users\User\personal-os-data"` — paths normalized, services start

---

## Files to Touch

### New Files

- `scripts/preflight.sh` — comprehensive preflight validation
- `scripts/cleanup-portable.sh` — credential and volume cleanup for portable
- `scripts/validate-restore.sh` — restore validation without executing
- `scripts/generate-backup-key.sh` — generate Fernet key for encryption
- `scripts/safe-eject.sh` — stop services and flush volumes before unplugging
- `docker-compose.portable.yml` — optional override with tuned timeouts for slow drives
- `docs/portable-mode.md` — portable USB/capsule deployment guide
- `docs/update-safety.md` — update, rollback, and restore procedures
- `tests/test_portable_install.py` — integration test suite for portable mode
- `tests/test_portable_migration.py` — USB migration and multi-host scenarios

### Modified Files

- `scripts/bootstrap.sh` — accept `--data-dir` flag; call `preflight.sh`; add portable mode checks
- `scripts/bootstrap.ps1` — Windows equivalents; path normalization; feature parity
- `scripts/update.sh` — enhanced rollback validation; audit logging
- `scripts/preflight-update.sh` — validate key, test backup export, verify rollback
- `scripts/rollback-last-update.sh` — auto-restore if migrations changed
- `scripts/restore.sh` — call `validate-restore.sh` before importing
- `scripts/restore-drill.sh` — full profile support; encryption key testing; integrity checks
- `docker-compose.yml` — use `${PERSONAL_OS_DATA_DIR:-./data}` for volume paths; use `${COMPOSE_PROJECT_NAME}` for named volumes
- `docs/install.md` — link to portable mode guide; mention preflight
- `README.md` — brief mention of portable mode; link to guide
- `.env.example` — add `PERSONAL_OS_DATA_DIR`, `BACKUP_ENCRYPTION_KEY` with descriptions
- `justfile` (Makefile) — add targets: `preflight`, `update-safe`, `restore-validate`, `cleanup`

---

## Suggested Executor Instructions

### Phase 1: Preflight and Portable Configuration (1-2 days)

1. **Create `scripts/preflight.sh`** (3 hours)
   - Docker, git, python3, curl version checks
   - RAM and disk space checks
   - Port availability check
   - Output: structured OK/warn/fail with remediation hints
   - Test on clean machine with missing optional tools

2. **Update `bootstrap.sh`**  (2 hours)
   - Accept `--data-dir` flag
   - Call `preflight.sh` before creating directories
   - Create data dir if missing; validate writability
   - Document in help: `./scripts/bootstrap.sh --data-dir /mnt/usb --core`

3. **Update `docker-compose.yml`** (1.5 hours)
   - Use `${PERSONAL_OS_DATA_DIR:-./data}` for all volume mounts
   - Use `${COMPOSE_PROJECT_NAME:-personal_os}` for named volumes
   - Test with: `PERSONAL_OS_DATA_DIR=/tmp/test docker compose --env-file .env config`

4. **Update `.env.example`** (30 min)
   - Add new vars with comments: `PERSONAL_OS_DATA_DIR`, `BACKUP_ENCRYPTION_KEY`

### Phase 2: Safe Update and Rollback (1-2 days)

5. **Enhance `preflight-update.sh`** (2 hours)
   - Validate encryption key (non-empty, ≥44 chars if Fernet)
   - Test backup export endpoint
   - Dry-run previous commit Docker build
   - Log to timestamped file

6. **Enhance `update.sh`** (2 hours)
   - Create `backups/update-YYYYmmdd-HHMMSS/` with backup artifact and metadata
   - Record git refs and backup path
   - After docker up, log summary
   - On failure, suggest rollback

7. **Enhance `rollback-last-update.sh`** (1.5 hours)
   - Validate previous commit builds
   - Prompt to restore database if migrations changed
   - Log to audit trail

### Phase 3: Restore Validation and Portability Safety (1 day)

8. **Create `scripts/validate-restore.sh`** (1.5 hours)
   - Read postgres dump; validate integrity
   - Count tables and rows
   - Estimate restore time
   - Support --dry-run

9. **Create `scripts/cleanup-portable.sh`** (1 hour)
   - Stop containers, remove volumes, optionally shred .env
   - Verify cleanup with `docker ps`, `docker volume ls`

10. **Enhance `scripts/restore-drill.sh`** (1.5 hours)
    - Support `--profile full`
    - Exercise all service migrations
    - Test backup encryption if key set
    - Log results

### Phase 4: Documentation (1 day)

11. **Create `docs/portable-mode.md`** (2 hours)
    - USB preparation and filesystem recommendations
    - Bootstrap command and preflight walkthrough
    - Data directory layout
    - Backup/restore procedures
    - Migration to new USB
    - Cleanup for safe unplug

12. **Create `docs/update-safety.md`** (1.5 hours)
    - Update workflow with preflight checks
    - Rollback procedures and recovery
    - Backup key management

13. **Update `docs/install.md`** and `README.md`** (30 min)
    - Link to portable guide
    - Mention `./scripts/preflight.sh` as first step

### Phase 5: Testing and Validation (1.5 days)

14. **Create integration and E2E tests** (2-3 hours)
    - `tests/test_portable_install.py` — bootstrap with --data-dir
    - `tests/test_portable_migration.py` — move data dir between mounts
    - Manual test checklist

### Optional Phase 6: Polish and Windows Parity (1 day)

15. **Update `bootstrap.ps1`** (2 hours)
    - Accept `-DataDir` parameter
    - Call Windows equivalent of preflight
    - Path normalization
    - Feature parity with bash

16. **Create `scripts/generate-backup-key.sh`** (1 hour)
    - Generate Fernet key
    - Prompt to save securely
    - Print to clipboard or file

---

## Acceptance Criteria Checklist

- [ ] **Portable USB/capsule mode is documented** → `docs/portable-mode.md` with USB prep, bootstrap, and cleanup steps
- [ ] **Runtime directories are configurable** → `PERSONAL_OS_DATA_DIR` env var; docker-compose.yml uses `${PERSONAL_OS_DATA_DIR:-./data}`; `--data-dir` flag in bootstrap.sh
- [ ] **No host credentials are persisted by default** → `scripts/cleanup-portable.sh` removes volumes and can shred .env; documentation recommends running before unplug
- [ ] **Preflight validates Docker, Tailscale, ADB, pnpm, Python, and disk space** → `scripts/preflight.sh` with comprehensive checks; fail on required, warn on optional; disk space and RAM validation
- [ ] **Update flow creates backup before changing services** → `preflight-update.sh` tests backup export; `update.sh` creates `backups/update-YYYYmmdd-HHMMSS/` with artifact and metadata
- [ ] **Restore drill command is documented or implemented** → `scripts/restore-drill.sh` enhanced to support `--profile full` and encryption key testing; documentation in `docs/update-safety.md`

