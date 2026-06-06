# Phase 4 Implementation: Mobile, Desktop, Auth Boundary, CI Coverage

Phase 4 converts the phase 1-3 foundation into a packaged multi-client system with a real gateway-first boundary and automated testing separated by subsystem.

## Defaults

- Web shell remains the canonical UI implementation.
- Mobile shell is Capacitor and consumes `apps/web/dist/spa`.
- Desktop shell is Tauri and consumes the same `apps/web/dist/spa`.
- API Gateway is the only service the clients should call in production.
- Sync, module, and command services still expose local ports for development, but they also enforce bearer-token validation when `AUTH_REQUIRED=true`.

## Authentication model

Device registration is public:

```http
POST /api/devices/register
```

It returns a short-lived access token and an opaque refresh token. The access token is an HMAC-signed JWT with:

- issuer and audience validation
- key id (`kid`) for rotation
- token id (`jti`) for session tracking
- scope list
- expiration and not-before checks

Refresh tokens are opaque random values. Only their SHA-256 hash is stored.

Auth endpoints:

```http
POST /api/auth/refresh
POST /api/auth/revoke
GET  /api/auth/session
```

The API gateway validates that access-token hashes exist in `auth_sessions`, are not expired, and are not revoked. Downstream services validate the token signature and scope. This keeps the gateway as the revocation authority and downstream services as independently protected local services.

## Gateway proxy boundary

Production clients should use:

```txt
VITE_API_URL=http://localhost:8080
VITE_SYNC_URL=http://localhost:8080/api/proxy/sync
VITE_MODULE_API_URL=http://localhost:8080/api/proxy/modules
VITE_COMMAND_BUS_URL=http://localhost:8080/api/proxy/commands
```

Gateway proxy routes:

```http
/api/proxy/sync/{path}
/api/proxy/modules/{path}
/api/proxy/commands/{path}
```

Read methods require `*:read` scopes; write methods require `*:write` or `command:request`.

## Mobile packaging

Files:

```txt
apps/mobile/package.json
apps/mobile/capacitor.config.ts
apps/mobile/scripts/validate-capacitor-config.mjs
```

Commands:

```bash
pnpm --dir apps/mobile validate
pnpm --dir apps/mobile cap:add:android
pnpm --dir apps/mobile cap:sync
pnpm --dir apps/mobile android:debug
```

## Desktop packaging

Files:

```txt
apps/desktop/package.json
apps/desktop/src-tauri/Cargo.toml
apps/desktop/src-tauri/tauri.conf.json
apps/desktop/src-tauri/src/main.rs
apps/desktop/scripts/validate-tauri-config.mjs
```

Commands:

```bash
pnpm --dir apps/desktop validate
pnpm --dir apps/desktop test
pnpm --dir apps/desktop build
```

## Automated testing

Workflows are intentionally separated:

| Workflow | Purpose | Gate |
|---|---|---|
| `backend-unit.yml` | Pure backend logic by service | 95-100% coverage |
| `backend-integration.yml` | Docker Compose core health and auth smoke | all core services healthy |
| `frontend-web.yml` | Web unit tests, typecheck, SPA build | 90% frontend service coverage |
| `mobile-android.yml` | Capacitor config, sync, debug APK | APK artifact produced |
| `desktop-tauri.yml` | Tauri config, Rust fmt/test/build | desktop bundle artifact produced |
| `docker-compose.yml` | Compose profile validation and image builds | all profiles parse |
| `security.yml` | secret scan and pre-commit hygiene | no tracked env/secrets |

Coverage gates are strict on core pure logic now. Full API handler coverage requires database integration fixtures and should be raised incrementally as Phase 5 adds service-level testcontainers.
