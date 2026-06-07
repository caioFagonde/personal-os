# V1 Feature Matrix — Personal OS / Nexus Core

Generated: 2026-06-07  
Test baseline: `make certify-v1` — 24/24 pass

## Legend

| Status | Meaning |
|--------|---------|
| **Working** | Endpoint responds, UI renders, smoke test passes |
| **Partial** | Core path works, edge cases or advanced features pending |
| **Ext-config** | Requires external credentials or hardware (OAuth apps, Tailscale, Twilio) |
| **Dry-run** | Safe default — feature disabled until explicitly enabled |
| **Not impl** | Route exists, page renders, but backend logic is stub/placeholder |

---

## Module Matrix

| Module | Route | Backend | Status | Smoke test | Known gaps |
|--------|-------|---------|--------|------------|------------|
| Command Center | `/` | api-gateway | **Working** | `curl $API/health` | — |
| Capture | `/capture` | capture-service:8087 | **Working** | `/task`, `/note`, `/secretary` all tested | Secretary delegation requires SECRETARY_EMAIL/WHATSAPP |
| Tasks | `/tasks` | capture-service:8087 | **Working** | `GET/POST/PATCH /api/tasks` | — |
| Secretary delegation | via `/capture` | capture-service:8087 | **Ext-config** | Returns structured 409 when channels missing | Requires SECRETARY_EMAIL and/or SECRETARY_WHATSAPP |
| Zettelkasten | `/zettelkasten` | module-service:8083 | **Working** | `GET/POST /api/zettelkasten/notes` | — |
| Study | `/study` | module-service:8083 | **Working** | Notes list accessible | — |
| Study Companion | `/study-companion` | study-companion-service:8088 | **Working** | Text capture creates atoms and schedules | — |
| Analog capture | `/study-companion` | study-companion-service:8088 | **Partial** | Text path works; OCR/vision uses heuristic fallback | Full OCR requires model-runtime with real provider |
| Research / PDF | `/research` | research-service:8084 | **Working** | Search endpoint responds | PDF ingestion works for public/authorized URLs |
| Geospatial | `/geospatial` | module-service:8083 | **Working** | `GET /api/geospatial/memories` | TileServer GL restarts (optional) |
| AR Memory | `/ar-memory` | module-service:8083 | **Working** | `GET /api/ar-memory/anchors` | — |
| Automation | `/automation` | automation-service:8085 | **Working** | Health OK, workflow CRUD available | n8n webhook integration requires n8n setup |
| Notifications | via connectors | ntfy:80 | **Ext-config** | ntfy test button; subscription instructions shown | Requires NTFY_BASE_URL |
| Connectors | `/connectors` | connector-service:8094 | **Working** | Status endpoint returns per-provider config state | — |
| Connector Worker | `/connector-worker` | connector-service:8094 | **Working** | Worker status and tick endpoints | — |
| Google OAuth | `/connectors` | connector-service:8094 | **Ext-config** | Structured 409 if GOOGLE_CLIENT_ID missing | Requires Google Cloud OAuth app |
| Microsoft OAuth | `/connectors` | connector-service:8094 | **Ext-config** | Structured 409 if MICROSOFT_CLIENT_ID missing | Requires Azure AD app |
| Twilio | `/connectors` | connector-service:8094 | **Ext-config** | Dry-run test available | Requires TWILIO_ACCOUNT_SID etc. |
| ntfy | `/connectors` | connector-service:8094 | **Working** | Test button works; shows subscription help | — |
| Tailscale | `/connectors` | connector-service:8094 | **Ext-config** | CLI state detection; shows auth-required state | Requires Tailscale CLI and auth |
| Sync Health | `/sync-health` | sync-engine:8081 | **Working** | `GET /api/sync/health` | — |
| Offline Queue | `/offline-queue` | sync-engine:8081 | **Partial** | Page renders; queue visible when items exist | — |
| Conflicts | `/conflicts` | sync-engine:8081 | **Working** | `GET /api/sync/conflicts` | — |
| Backup & Restore | `/backup-restore` | connector-service:8094 | **Partial** | Export endpoint exists; restore is manual | Upload to Google Drive/OneDrive requires OAuth |
| Device Pairing | `/device-pairing` | api-gateway:8080 | **Partial** | Device registration works; QR is placeholder | — |
| Model Runtime | `/model-runtime` | model-runtime:8095 | **Working** | 3 runtimes (OCR, object, audio) in heuristic mode | Replace with real model providers for production |
| Digital Twin | `/digital-twin` | digital-twin-service:8086 | **Working** | Timeline, goals, recommendations available | — |
| Coding Agent | `/coding-agent` | coding-agent-service:8096 | **Dry-run** | Status shows execute_enabled=false, policy enforced | Requires `claude` binary and CODING_AGENT_EXECUTE=true |
| Certification | `/certification` | — | **Working** | Page renders certification checklist | — |
| Release Center | `/release-center` | api-gateway:8080 | **Working** | `GET /api/release` returns version info | — |
| Live Stack | `/live-stack` | — | **Working** | Page renders live service status | — |
| Initial Readiness | `/initial-readiness` | — | **Working** | Page renders readiness checklist | — |
| Onboarding | `/onboarding` | — | **Working** | Page renders first-run flow | — |

---

## Endpoints Verified

| Endpoint | Method | Status |
|----------|--------|--------|
| `/health` | GET | 200 |
| `/api/modules` | GET | 200 (16 modules) |
| `/api/devices/register` | POST | 200 |
| `/api/proxy/capture/api/capture` | POST | 200 |
| `/api/proxy/capture/api/tasks` | GET | 200 |
| `/api/proxy/capture/api/tasks` | POST | 200 |
| `/api/proxy/capture/api/tasks/{id}` | PATCH | 200 |
| `/api/proxy/capture/api/outbox` | GET | 200 |
| `/api/proxy/modules/api/zettelkasten/notes` | GET/POST | 200 |
| `/api/proxy/modules/api/geospatial/memories` | GET | 200 |
| `/api/proxy/modules/api/ar-memory/anchors` | GET | 200 |
| `/api/proxy/study-companion/api/study-companion/text` | POST | 200 |
| `/api/proxy/study-companion/api/study-companion/reviews` | GET | 200 |
| `/api/proxy/research/api/research/search` | GET | 200 |
| `/api/proxy/sync/api/sync/health` | GET | 200 |
| `/api/proxy/sync/api/sync/conflicts` | GET | 200 |
| `/api/proxy/automation/api/automation/workflows` | GET | 200 |
| `/api/proxy/digital-twin/api/digital-twin/timeline` | GET | 200 |
| `/api/proxy/connectors/api/connectors/status` | GET | 200 |
| `/api/proxy/connectors/api/connectors/worker/status` | GET | 200 |
| `/api/proxy/connectors/api/connectors/tailscale/status` | GET | 200 |
| `/api/proxy/model-runtime/health` | GET | 200 |
| `/api/proxy/coding-agent/api/coding-agent/status` | GET | 200 |
| `/api/proxy/coding-agent/api/coding-agent/jobs` | GET | 200 |

---

## Service Ports

| Service | Container port | Host port | Health |
|---------|---------------|-----------|--------|
| api-gateway | 8080 | 8080 | Healthy |
| sync-engine | 8081 | 8081 | Healthy |
| command-bus | 8082 | 8082 | Healthy |
| module-service | 8083 | 8083 | Healthy |
| research-service | 8084 | 8084 | Healthy |
| automation-service | 8085 | 8085 | Healthy |
| digital-twin-service | 8086 | 8086 | Healthy |
| capture-service | 8087 | 8092 | Healthy |
| study-companion-service | 8088 | 8093 | Healthy |
| connector-service | 8094 | 8094 | Healthy |
| model-runtime | 8095 | 8095 | Healthy |
| coding-agent-service | 8096 | 8096 | Healthy |
| web | 9000 | 9000 | Up |
| postgres | 5432 | 5432 | Healthy |
| nats | 4222 | 4222 | Healthy |
| minio | 9000 | 9010 | Healthy |

---

## External Configuration Requirements

| Feature | Required env vars | Purpose |
|---------|------------------|---------|
| Google OAuth | GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET | Google Calendar/Drive/Gmail |
| Microsoft OAuth | MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET | Outlook/OneDrive |
| Twilio | TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER | SMS/WhatsApp |
| Secretary delegation | SECRETARY_EMAIL, SECRETARY_WHATSAPP | Message routing targets |
| Coding agent | CODING_AGENT_EXECUTE=true + `claude` CLI | Claude Code job execution |
| Tailscale | TS_AUTHKEY (compose), tailscale CLI | Private mesh networking |
| ntfy | NTFY_BASE_URL (defaults to ntfy container) | Push notifications |
