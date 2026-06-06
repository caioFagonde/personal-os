# Sync protocol

The sync system is append-only and device-aware.

Write path:

1. Client writes locally first.
2. Client appends a pending change with vector clock and entity payload.
3. Client pushes to `/api/sync/push`.
4. Server records `entity_versions` and `sync_log`.
5. Other devices pull with `/api/sync/pull` by cursor and module filter.

Conflict strategy:

- `lww`: acceptable for simple metadata.
- `field_merge`: acceptable for settings and structured logs.
- `crdt_text`: required for notes, annotations, reflections, and long-form text.
- `set_union`: tags, backlinks, memberships.
- `counter`: habit counts, streak increments.
- `manual`: destructive operations and command side effects.

Attachments sync through MinIO object keys plus checksum validation in `attachments`.
