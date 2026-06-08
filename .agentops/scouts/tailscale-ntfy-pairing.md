# Scout Report: Tailscale + ntfy Pairing & Notifications

**Task:** `tailscale-ntfy-pairing` — Phone pairing, Tailscale private URL, and ntfy notification setup  
**Scout role:** Read-only architecture assessment  
**Date:** 2026-06-08  
**Status:** Ready for implementation  

---

## Executive Summary

Device pairing and notifications infrastructure exists but **lacks critical user-facing guidance**:

✅ **Strengths:**
- Device pairing backend is in place (15-min expiring codes, QR generation)
- Tailscale detection endpoint exists
- ntfy dry-run/test infrastructure complete
- Provider manifests well-defined (ntfy, Tailscale)
- Database schema supports pairing, device tracking with `tailscale_ip` column
- Connector marketplace UI shows provider states and setup guidance

⚠️ **Critical Gaps:**
- **DevicePairingPage shows only public URL** — no distinction between local/Tailscale/private URLs
- **Missing setup guidance UI** when Tailscale or ntfy are unconfigured (shows raw error instead)
- **ntfy subscription state unclear** — no "subscribe to topic" or "view subscription" UI
- **No Tailscale IP display** on pairing page (users can't see what IP their phone will connect to)
- **Local network detection missing** — no way to show `http://localhost:PORT` alongside public URL
- **No test/dry-run flow for pairing** (can test ntfy, not pairing itself)

---

## Relevant Files

### Frontend (Pages & Components)

| File | Status | Purpose | Needs |
|------|--------|---------|-------|
| `apps/web/src/pages/DevicePairingPage.vue` | ⚠️ Partial | QR generation, pairing URL display | Local/Tailscale URL detection, setup guidance |
| `apps/web/src/pages/ConnectorsPage.vue` | ✅ Complete | Provider marketplace, ntfy/Tailscale test | Integrates dry-run, shows setup errors |
| `apps/web/src/pages/SettingsPage.vue` | ⚠️ Partial | Provider config, service health | No ntfy subscription UI |
| `apps/web/src/components/ProviderCard.vue` | ✅ Complete | Provider state display, config expansion | Works as-is |
| `apps/web/src/providers/manifests.ts` | ✅ Complete | Provider defs: ntfy, Tailscale, etc. | Well-structured |

### Backend (Services)

| File | Status | Purpose | Needs |
|------|--------|---------|-------|
| `services/connector-service/app/main.py:787–814` | ✅ Complete | POST `/api/connectors/device-pairing`, GET `/api/connectors/device-pairing/qr` | Return local/Tailscale URLs in pairing response |
| `services/connector-service/app/main.py:504–513` | ✅ Complete | POST `/api/connectors/ntfy/test` — dry-run & execute | No changes needed |
| `services/connector-service/app/main.py:682–685` | ✅ Complete | GET `/api/connectors/tailscale/status` | Return full status object |
| `services/connector-service/app/providers.py:241–246` | ✅ Complete | `provider_status_from_env()` for ntfy, Tailscale | Works as-is |
| `services/api-gateway/app/main.py:288–325` | ✅ Complete | POST `/api/devices/register` — device registration with `tailscale_ip` | Accepts Tailscale IP, stores in DB |

### Database (Migrations)

| Schema | File | Status |
|--------|------|--------|
| `device_pairing_codes` | `infra/postgres/migrations/009_phase_10_connectors_continuity.sql:73–82` | ✅ Complete |
| `devices` (tailscale_ip column) | `infra/postgres/migrations/001_core.sql` | ✅ Complete |
| `connector_accounts` (ntfy, Tailscale rows) | `infra/postgres/migrations/009_phase_10_connectors_continuity.sql:84–91` | ✅ Complete |

### Configuration & Environment

| Key | Current | Needed |
|-----|---------|--------|
| `CONNECTOR_PUBLIC_BASE_URL` | `${CONNECTOR_PUBLIC_BASE_URL:-http://localhost:8080}` (docker-compose.yml:339) | Correct; used in pairing URL generation |
| `NTFY_BASE_URL` | `${NTFY_BASE_URL:-http://ntfy:80}` | Correct; allows self-hosted ntfy |
| `NTFY_TOPIC` | `${NTFY_TOPIC:-personal-os-dev}` | Correct; topic for all notifications |
| `TAILSCALE_AUTHKEY` | `${TAILSCALE_AUTHKEY:-}` | Optional; for automated sign-in |
| `TAILSCALE_HOSTNAME` | `${TAILSCALE_HOSTNAME:-personal-os-dev}` | Correct; human-readable Tailscale hostname |

---

## Acceptance Criteria Assessment

### 1. **Pair Device page clearly shows local URL and Tailscale/private URL when detectable**
- ❌ **FAIL (current)**
  - Page shows only `pairing.url` from backend (`CONNECTOR_PUBLIC_BASE_URL`)
  - No local URL (`http://localhost:8080/device-pairing?code=...`)
  - No Tailscale hostname or IP (`https://personal-os-dev.{tailnet}/...`)
  - **Required:** Backend returns multiple URL variants; frontend displays with labels

### 2. **QR pairing UX is clear and safe**
- ✅ **PASS (current)**
  - QR code generated server-side (SVG)
  - Safe: no secrets in QR payload
  - Copy buttons for code and URL
  - 15-min expiration message shown
  - Approval warning present ("Approve only devices you physically control")

### 3. **ntfy setup has subscribe/test/dry-run states**
- ⚠️ **PARTIAL (current)**
  - ✅ Dry-run test available (POST `/api/connectors/ntfy/test` with `execute: false`)
  - ✅ Full test available (POST with `execute: true`)
  - ❌ No UI to view subscription status
  - ❌ No UI to subscribe to ntfy topic (users must know topic in advance)
  - ❌ No "copy ntfy topic" shortcut for mobile subscription

### 4. **Missing Tailscale or ntfy config shows setup guidance, not raw error**
- ⚠️ **PARTIAL (current)**
  - ✅ ConnectorsPage shows provider state (needs_config, etc.) with expansion panel
  - ✅ Missing env vars are listed in expansion
  - ⚠️ Error handling in `ConnectorsPage.vue:239–251` (describeConnectorError) attempts to parse JSON errors
  - ❌ DevicePairingPage shows raw error message if pairing endpoint fails (no structured guidance)
  - **Risk:** If ntfy/Tailscale are not configured, pairing endpoint doesn't fail gracefully

### 5. **No automatic public exposure is introduced**
- ✅ **PASS (confirmed)**
  - CLAUDE.md forbids arbitrary unauthenticated remote shell
  - Pairing requires scoped device registration with approval
  - No public webhooks or listening ports exposed
  - Tailscale auth is opt-in (TAILSCALE_AUTHKEY)
  - ntfy topics are private by default (custom `NTFY_TOPIC`)

### 6. **Tests cover pairing/config contracts**
- ⚠️ **PARTIAL (needs expansion)**
  - ✅ `tests/test_connector_marketplace.py` covers connector status
  - ✅ `services/connector-service/tests/test_providers.py` covers provider status logic
  - ❌ No tests for device pairing code generation/expiration
  - ❌ No tests for Tailscale IP assignment to devices
  - ❌ No E2E test for pairing → device registration → Tailscale IP flow
  - **Required:** Add integration tests for pairing contract

---

## Implementation Points & Risks

### High Priority (Blocking Acceptance)

#### 1. **Enhance Device Pairing Response** (Backend)
**File:** `services/connector-service/app/main.py:787–802`

Current response:
```json
{
  "pairing_id": "...",
  "pairing_code": "...",
  "expires_in_seconds": 900,
  "url": "http://localhost:8080/device-pairing?code=..."
}
```

**Required:** Add URL variants:
```json
{
  "pairing_id": "...",
  "pairing_code": "...",
  "expires_in_seconds": 900,
  "urls": {
    "public": "http://localhost:8080/device-pairing?code=...",
    "local": "http://localhost:8080/device-pairing?code=...",
    "tailscale": "https://personal-os-dev.{tailnet}/device-pairing?code=..." // or null
  },
  "tailscale_hostname": "personal-os-dev",
  "tailscale_configured": true
}
```

**How to get Tailscale status in pairing endpoint:**
- Call `provider_status_from_env()` for "tailscale" (line 31 already imports)
- If `status.configured`, extract `TAILSCALE_HOSTNAME` from env
- Generate MagicDNS URL: `https://{hostname}.{tailnet}/...` ← requires tailnet detection (may not be available at generate time; make optional)
- If Tailscale not configured, set `tailscale_configured: false`, `tailscale_hostname: null`

**Risks:**
- Tailnet name not available without Tailscale CLI → make URL nullable, document that user must substitute `{tailnet}`
- Local URL may not match public URL if `CONNECTOR_PUBLIC_BASE_URL` is not `localhost:8080` → always include actual `CONNECTOR_PUBLIC_BASE_URL`

---

#### 2. **Update DevicePairingPage to Show Multiple URLs** (Frontend)
**File:** `apps/web/src/pages/DevicePairingPage.vue:13–31`

Current: Shows single `pairing.url` in input.

**Required:**
```vue
<template>
  <q-card v-if="pairing" class="glass-card">
    <q-card-section class="row q-col-gutter-lg items-stretch">
      <div class="col-12 col-md-4">
        <img :src="qrUrl" alt="Pairing QR code" class="pairing-qr" />
      </div>
      <div class="col-12 col-md-8">
        <div class="text-h6 q-mb-md">Pairing URLs</div>
        
        <!-- Public/Default URL -->
        <div class="q-mb-md">
          <div class="text-caption text-weight-bold q-mb-xs">
            <q-icon name="mdi-cloud-outline" size="14px" class="q-mr-xs" />
            Public URL (remote access, firewall-friendly)
          </div>
          <q-input readonly :model-value="pairing.urls.public" dense outlined>
            <template #append><q-btn flat icon="mdi-content-copy" @click="copy(pairing.urls.public)" /></template>
          </q-input>
        </div>

        <!-- Local URL (if different from public) -->
        <div class="q-mb-md" v-if="pairing.urls.local !== pairing.urls.public">
          <div class="text-caption text-weight-bold q-mb-xs">
            <q-icon name="mdi-lan" size="14px" class="q-mr-xs" />
            Local URL (same network, faster)
          </div>
          <q-input readonly :model-value="pairing.urls.local" dense outlined>
            <template #append><q-btn flat icon="mdi-content-copy" @click="copy(pairing.urls.local)" /></template>
          </q-input>
        </div>

        <!-- Tailscale URL (if configured) -->
        <div class="q-mb-md" v-if="pairing.tailscale_configured">
          <div class="text-caption text-weight-bold q-mb-xs">
            <q-icon name="mdi-lan-connect" size="14px" class="q-mr-xs" />
            Tailscale Private URL (private mesh, best security)
          </div>
          <q-banner v-if="!pairing.urls.tailscale" class="bg-info text-white q-mb-sm" dense rounded>
            <q-icon name="mdi-information-outline" />
            Tailscale detected but MagicDNS URL not auto-generated. 
            Visit <a href="https://login.tailscale.com" target="_blank" rel="noopener" style="color:inherit;text-decoration:underline">Tailscale admin console</a> 
            and copy your Tailnet name (e.g., <code>example.ts.net</code>), then:
            <code>https://personal-os-dev.YOURNAME.ts.net/device-pairing?code=...</code>
          </q-banner>
          <q-input v-if="pairing.urls.tailscale" readonly :model-value="pairing.urls.tailscale" dense outlined>
            <template #append><q-btn flat icon="mdi-content-copy" @click="copy(pairing.urls.tailscale)" /></template>
          </q-input>
        </div>

        <!-- Pairing Code -->
        <div class="q-mb-md">
          <div class="text-caption text-weight-bold q-mb-xs">Pairing Code (type on phone if QR unavailable)</div>
          <q-input readonly :model-value="pairing.pairing_code" dense outlined>
            <template #append><q-btn flat icon="mdi-content-copy" @click="copy(pairing.pairing_code)" /></template>
          </q-input>
        </div>

        <p class="text-caption" style="color:var(--nexus-muted)">
          <q-icon name="mdi-timer-outline" size="14px" class="q-mr-xs" />
          Expires in {{ pairing.expires_in_seconds }} seconds. Approve only devices you physically control.
        </p>
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup lang="ts">
// ... existing imports ...

const pairing = ref<any | null>(null)

async function create() {
  creating.value = true
  error.value = ''
  try {
    pairing.value = await jsonFetch(`${connectorsUrl}/api/connectors/device-pairing`, {
      method: 'POST',
      body: JSON.stringify({}),
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    creating.value = false
  }
}
</script>
```

**Risks:**
- Tailscale MagicDNS URL requires Tailnet name; if not available, show guidance
- URLs may be long; ensure mobile display doesn't overflow (use dense `q-input`)
- Update `qrUrl` to use `pairing.urls.public` (or configurable)

---

#### 3. **Handle Missing Tailscale/ntfy in Pairing** (Backend & Frontend)
**Files:** `services/connector-service/app/main.py:787–802`, `apps/web/src/pages/DevicePairingPage.vue`

**Problem:** If pairing endpoint fails (e.g., database down), users see raw error.

**Solution (Backend):**
- Catch exceptions in `create_pairing_code()` 
- Return structured error with next action:
  ```json
  {
    "error": "pairing_creation_failed",
    "message": "Failed to generate pairing code",
    "action": "check_services",
    "hint": "Restart connector-service: docker compose restart connector-service"
  }
  ```

**Solution (Frontend):**
- Parse error response; show actionable banner instead of raw text
- Example in `ConnectorsPage.vue:239–251` (describeConnectorError)

---

### Medium Priority (Improves UX)

#### 4. **Add ntfy Subscription UI** (Frontend)
**File:** `apps/web/src/pages/ConnectorsPage.vue`

Current: ntfy test shows dry-run result (topic name).

**Required:**
- Add "Subscribe to ntfy topic" button or modal
- Show instructions for mobile subscription (e.g., "Add this link to your phone: https://ntfy.sh/personal-os-dev")
- Display current topic name (from `/api/connectors/ntfy/test` result)
- Optional: QR code for ntfy subscription link

**Sketch:**
```vue
<q-btn v-if="mf.id === 'ntfy' && st.configured" outline color="primary" size="sm" label="View topic & subscribe" @click="showNtfySubscription(st)" />
```

---

#### 5. **Tailscale IP Display in Device Pairing** (Future Phase)
**File:** `apps/web/src/pages/DevicePairingPage.vue` (Phase 13+)

Once devices register with Tailscale IPs, show expected IP:
```json
{
  "expected_tailscale_ip": "100.xxx.xxx.xxx (if already registered)"
}
```

Current: No Tailscale IP assignment endpoint; this is Phase 13+ work.

---

### Low Priority (Polish & Testing)

#### 6. **Test Coverage for Device Pairing**
**Files:** `tests/test_phase10_scaffold.py` or new `tests/test_device_pairing.py`

**Required tests:**
- POST `/api/connectors/device-pairing` returns valid code + URL
- Code expires after 15 minutes
- QR SVG endpoint returns valid SVG
- Tailscale configured → response includes `tailscale_configured: true`
- Tailscale not configured → response includes `tailscale_configured: false, urls.tailscale: null`

---

## Risks & Conflicts

### 1. **Tailscale MagicDNS Unavailable at Pairing Time**
- **Risk:** Tailscale hostname is configured, but Tailnet name is not available in env
- **Mitigation:** 
  - Document that `TAILSCALE_AUTHKEY` only auto-signs; user must manually link for MagicDNS
  - Show guidance banner if Tailscale is configured but Tailnet not detected
  - Allow manual Tailnet entry in settings

### 2. **Local Network URL May Not Be `localhost:8080`**
- **Risk:** In production, `CONNECTOR_PUBLIC_BASE_URL` might be `https://example.com`, but local URL is `http://192.168.1.100:8080`
- **Mitigation:**
  - Backend should also return detected local IP(s) if available
  - Frontend shows all available URLs with labels
  - Document that users may need to substitute IP/hostname manually

### 3. **ntfy Topic Not Stored Persistently**
- **Risk:** If user changes `NTFY_TOPIC` in env, pairing codes and old connections still reference old topic
- **Mitigation:**
  - Store active topic in `connector_accounts.settings` JSONB
  - Migration to denormalize topic name for audit trail
  - Document that changing `NTFY_TOPIC` requires manual re-subscription

### 4. **Public URL Exposure if `CONNECTOR_PUBLIC_BASE_URL` is Misconfigured**
- **Risk:** If admin sets `CONNECTOR_PUBLIC_BASE_URL` to public domain without auth, pairing codes are guessable
- **Mitigation:**
  - Pairing codes are 18-byte URL-safe random (crypto.secrets.token_urlsafe)
  - 15-min expiration limits attack window
  - Log pairing code generation for audit
  - Document security implications in CLAUDE.md

### 5. **Tailscale Mesh Not Yet Fully Integrated into Device Registration**
- **Risk:** Device registers with `tailscale_ip`, but sync/pairing doesn't use it yet (Phase 13+ work)
- **Mitigation:**
  - Current: endpoint accepts `tailscale_ip` but doesn't validate ownership
  - Phase 13: validate IP matches device's Tailscale enrollment
  - For now, document that Tailscale IP is informational

---

## Tests to Run

### Unit Tests
```bash
# Connector provider status logic
python3 -m pytest services/connector-service/tests/test_providers.py -v

# OAuth and device registration
python3 -m pytest services/connector-service/tests/test_oauth.py -v
python3 -m pytest services/api-gateway/tests/test_*.py -v
```

### Integration Tests (require Docker)
```bash
# Full bootstrap
./scripts/bootstrap.sh --full

# Connector marketplace and provider status
python3 -m pytest tests/test_connector_marketplace.py -v

# Device pairing (if new test added)
python3 -m pytest tests/test_device_pairing.py -v
```

### Manual Testing
```bash
# 1. Generate pairing code
curl -X POST http://localhost:8094/api/connectors/device-pairing

# 2. Test ntfy (dry-run)
curl -X POST http://localhost:8094/api/connectors/ntfy/test \
  -H "Content-Type: application/json" \
  -d '{"execute": false}'

# 3. Check Tailscale status
curl http://localhost:8094/api/connectors/tailscale/status

# 4. Check connector status
curl http://localhost:8094/api/connectors
```

---

## Suggested Executor Instructions

### Phase 1: Backend URL Variants (1–2 hours)

**Task:**
1. Modify `services/connector-service/app/main.py:787–802`
   - Import `provider_status_from_env` (already imported at line 29)
   - Detect Tailscale config in pairing response
   - Return `urls: {public, local?, tailscale?}` instead of single `url`
   - Include `tailscale_configured` and `tailscale_hostname` flags

2. Add test: `services/connector-service/tests/test_device_pairing.py`
   - POST pairing endpoint returns structured response
   - Tailscale configured → response includes Tailscale fields
   - Tailscale not configured → response includes `tailscale_configured: false`

**Risks:** None; response is additive (old `url` can be deprecated in Phase 2)

---

### Phase 2: Frontend Display (2–3 hours)

**Task:**
1. Refactor `apps/web/src/pages/DevicePairingPage.vue`
   - Parse new `pairing.urls` and `pairing.tailscale_configured`
   - Render multiple input cards with labels (public, local, Tailscale)
   - Hide Tailscale card if not configured
   - Show Tailnet guidance banner if Tailscale configured but URL unavailable

2. Manual testing: Pair device on local network, Tailscale, and remote

**Risks:** 
- Mobile responsiveness: ensure cards stack on small screens
- Copy button accessibility

---

### Phase 3: ntfy Subscription UI (1–2 hours)

**Task:**
1. Add "Subscribe" modal to `apps/web/src/pages/ConnectorsPage.vue`
   - Show ntfy topic (from test result or from env)
   - QR code for mobile subscription link
   - Copy button for https://ntfy.sh/{topic}

2. Manual test: Subscribe on phone, send test notification

**Risks:** ntfy subscription is out-of-app; document in UI

---

### Phase 4: Error Handling & Tests (1–2 hours)

**Task:**
1. Add try-catch to pairing endpoint; return structured error
2. Update DevicePairingPage to parse and display error guidance
3. Add E2E test: bootstrap → create pairing → check response structure
4. Add test: Tailscale not configured → pairing response reflects that

**Risks:** Error messages must not expose secrets or server paths

---

## Summary

| Item | Status | Effort | Priority |
|------|--------|--------|----------|
| Backend URL variants | ❌ TODO | 1–2h | HIGH |
| Frontend display (public/local/Tailscale) | ❌ TODO | 2–3h | HIGH |
| Error handling & guidance | ⚠️ Partial | 1–2h | HIGH |
| ntfy subscription UI | ❌ TODO | 1–2h | MEDIUM |
| Test coverage (pairing, Tailscale, ntfy) | ⚠️ Partial | 2h | MEDIUM |
| Tailscale IP display (device tracking) | ❌ Deferred | — | Phase 13+ |

**Total effort to acceptance:** ~7–10 hours (staggered across phases 1–4)

