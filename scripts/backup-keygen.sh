#!/usr/bin/env bash
# Generate the age keypair for encrypted backups (Phase E4).
# The PRIVATE key is printed ONCE and never stored in the repo/data dirs — save
# it in a password manager. The PUBLIC key goes in .env as BACKUP_AGE_RECIPIENT.
set -Eeuo pipefail
if ! command -v age-keygen >/dev/null 2>&1; then
  cat >&2 <<'MSG'
age-keygen not found. Install age first:
  Debian/Ubuntu:  sudo apt install age
  macOS:          brew install age
Then re-run: scripts/backup-keygen.sh
MSG
  exit 3
fi
KEY_OUT="${1:-}"
if [[ -z "$KEY_OUT" ]]; then
  echo "Usage: scripts/backup-keygen.sh /secure/path/outside/repo/nexus-backup.agekey" >&2
  exit 2
fi
case "$KEY_OUT" in
  */secrets/*|*/.private/*|*/data/*|*/backups/*|"$PWD"/*)
    echo "Refusing to write the private key inside the repo/data dirs. Choose a path in your password-manager vault or an external location." >&2
    exit 2 ;;
esac
age-keygen -o "$KEY_OUT"
PUB="$(age-keygen -y "$KEY_OUT")"
cat <<MSG

────────────────────────────────────────────────────────────────
Backup age keypair created.
Private key: $KEY_OUT   (store in a password manager; NEVER commit)
Public key : $PUB

Add to .env:
  BACKUP_AGE_RECIPIENT=$PUB
  BACKUP_ENCRYPT=true

WARNING: if you lose the private key, encrypted backups are UNRECOVERABLE.
Keep an unencrypted local copy (BACKUP_ENCRYPT_LOCAL=false) only if your disk
is itself trusted/encrypted.
────────────────────────────────────────────────────────────────
MSG
