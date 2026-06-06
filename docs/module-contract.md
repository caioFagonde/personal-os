# Module contract

Every module must include `modules/<id>/manifest.yaml` and should expose optional migrations and API routers.

Required manifest keys:

- `id`
- `name`
- `version`
- `routes.web`
- `routes.api`
- `permissions`
- `events.publishes`
- `events.subscribes`
- `storage.tables`
- `sync.enabled`
- `sync.strategy`

Module startup sequence:

1. API gateway scans manifests.
2. Manifest is validated against `packages/module-manifest/schema/module-manifest.schema.json`.
3. Registry row is upserted into `modules`.
4. Routes, permissions, events, sync status, and health are exposed at `/api/modules`.
