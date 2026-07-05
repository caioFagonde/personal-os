#!/usr/bin/env bash
# Prune old snapshots per retention policy (Phase E4): keep 7 daily / 4 weekly /
# 6 monthly, and NEVER delete the only verified copy. Dry-run by default.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
: "${BACKUP_DIR:=backups}"
EXECUTE=false
[[ "${1:-}" == "--execute" ]] && EXECUTE=true

mapfile -t PLAN < <(python3 - "$BACKUP_DIR" <<'PY'
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, "scripts")
from backup.manifest import load_manifest
from backup.prune import Snapshot, plan_prune

backup_dir = Path(sys.argv[1])
snaps = []
if backup_dir.is_dir():
    for d in backup_dir.iterdir():
        if not d.is_dir():
            continue
        m = load_manifest(d)
        if not m:
            continue  # no manifest ⇒ incomplete ⇒ ignored by prune
        try:
            created = datetime.fromisoformat(m["created_at"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        verified = bool(m.get("verify_status") == "verified")
        snaps.append(Snapshot(d.name, created, verified))
keep, delete = plan_prune(snaps)
for bid in delete:
    print(f"DELETE {bid}")
for bid in keep:
    print(f"KEEP {bid}")
PY
)

for line in "${PLAN[@]}"; do
  action="${line%% *}"; bid="${line#* }"
  if [[ "$action" == "DELETE" ]]; then
    if $EXECUTE; then
      rm -rf "${BACKUP_DIR:?}/${bid}" && echo "[prune] deleted ${bid}"
    else
      echo "[prune] would delete ${bid}"
    fi
  fi
done
$EXECUTE || echo "[prune] dry-run — pass --execute to apply. Verified copies are always retained."
