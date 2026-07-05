"""Pure backup logic (Phase E4): manifest build/verify + retention policy.

Orchestration lives in the sibling shell scripts (backup-v2.sh, backup-verify.sh,
backup-prune.sh, backup-remote.sh); this package holds only side-effect-free
logic so it unit-tests without Postgres, rclone, age, or MinIO present.
"""
