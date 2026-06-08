# Safe update pipeline

Run `./scripts/update.sh --dry-run` to inspect the sequence. A real update calls `scripts/preflight-update.sh`, which blocks without `BACKUP_ENCRYPTION_KEY` and requests an encrypted connector backup before any Docker rebuild. It then rebuilds and starts the full profile. Source retrieval remains an explicit operator step; the script never performs an implicit `git pull`.

When `NTFY_BASE_URL` and `NTFY_TOPIC` are exported, preflight and update milestones are published. Notification failure does not interrupt backup or update safety. `scripts/rollback-last-update.sh` is dry-run by default; `--execute` requires a clean worktree and performs another backup preflight first.
