<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Setup" title="Settings" subtitle="Validate connector and cloud configuration before restarting services." />
    <q-banner v-if="message" :class="failed ? 'bg-negative text-white' : 'bg-positive text-white'" rounded>{{ message }}</q-banner>
    <q-card class="glass-card">
      <q-card-section><div class="text-h6">Provider configuration</div></q-card-section>
      <q-card-section><NexusConfigForm :fields="fields" @save="save" /></q-card-section>
    </q-card>
    <q-card class="glass-card">
      <q-card-section><div class="text-h6">Notifications</div></q-card-section>
      <q-card-section>
        <q-input
          v-model="phoneNumber"
          outlined
          label="Phone number for notifications"
          hint="E.164 format, e.g. +15551234567"
          :rules="[v => !v || /^\+[1-9]\d{7,14}$/.test(v) || 'Use E.164 format, e.g. +15551234567']"
        />
      </q-card-section>
    </q-card>
    <q-card class="glass-card" data-testid="vault-settings">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Obsidian vault</div>
        <div v-if="vaultStatus" class="q-mb-md">
          <div class="row q-gutter-sm items-center">
            <q-badge :color="vaultStatus.write_enabled ? 'positive' : 'warning'" :label="vaultStatus.write_enabled ? 'write enabled' : 'dry-run only'" />
            <span class="text-caption" style="color:var(--nexus-muted)">{{ vaultStatus.vault_path }}</span>
          </div>
          <div class="text-caption q-mt-xs" style="color:var(--nexus-muted)">
            files: {{ vaultFileSummary }} · conflicts: {{ vaultStatus.conflicts }}
            <span v-if="vaultStatus.last_run"> · last {{ vaultStatus.last_run.last_phase }} {{ vaultStatus.last_run.at }}</span>
          </div>
        </div>
        <div v-else class="text-caption q-mb-md" style="color:var(--nexus-muted)">
          Vault not configured. Set OBSIDIAN_VAULT_PATH in .env and restart connector-service.
        </div>
        <div class="row q-gutter-sm">
          <q-btn outline size="sm" icon="mdi-check-decagram-outline" label="Validate path" :loading="vaultBusy" @click="validateVault" />
          <q-btn outline size="sm" icon="mdi-magnify-scan" label="Index vault" :loading="vaultBusy" @click="indexVault" />
          <q-btn outline size="sm" icon="mdi-sync" label="Sync (dry-run)" :loading="vaultBusy" @click="runVaultSync(false)" />
          <q-btn
            v-if="vaultStatus && !vaultStatus.write_enabled"
            unelevated color="warning" text-color="dark" size="sm" icon="mdi-pencil-lock-outline"
            label="Enable vault write" @click="confirmEnable = true" data-testid="vault-enable"
          />
          <q-btn
            v-else-if="vaultStatus?.write_enabled"
            unelevated color="primary" size="sm" icon="mdi-sync" label="Sync now (writes)"
            :loading="vaultBusy" @click="runVaultSync(true)"
          />
        </div>
        <div v-if="vaultMessage" class="text-caption q-mt-sm">{{ vaultMessage }}</div>
      </q-card-section>
    </q-card>

    <q-dialog v-model="confirmEnable">
      <q-card class="glass-card" style="max-width: 480px">
        <q-card-section>
          <div class="text-h6">Enable vault write?</div>
          <p class="q-mt-sm">
            Nexus will write markdown into the mapped vault roots (Projects, Daily, Notes, Decisions…).
            A one-time backup of those roots is created first
            (<code>Backups/vault-pre-nexus-&lt;timestamp&gt;.tar.gz</code>).
            Deletes are never propagated in either direction.
          </p>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn unelevated color="warning" text-color="dark" label="Back up and enable" v-close-popup @click="enableVault" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Interface</div>
        <q-toggle
          :model-value="density === 'compact'"
          label="Compact density"
          data-testid="density-toggle"
          @update:model-value="setDensity($event ? 'compact' : 'comfortable')"
        />
        <div class="text-caption" style="color:var(--nexus-muted)">
          Compact tightens paddings across lists and cards — more rows per screen, same type size.
        </div>
      </q-card-section>
    </q-card>
    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Service health</div>
        <q-btn outline color="primary" label="Check services" icon="mdi-heart-pulse" @click="checkServices" />
        <div v-if="serviceStatus.length" class="q-mt-md column q-gutter-xs">
          <q-chip
            v-for="svc in serviceStatus"
            :key="svc.name"
            :color="svc.ok ? 'positive' : 'negative'"
            text-color="white"
            :icon="svc.ok ? 'mdi-check-circle' : 'mdi-alert-circle'"
          >{{ svc.name }}</q-chip>
        </div>
      </q-card-section>
    </q-card>
    <q-banner class="bg-warning text-dark" rounded>
      Restart the affected optional service after saving, for example <code>docker compose --env-file .env restart connector-service</code>.
    </q-banner>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import NexusConfigForm, { type ConfigField } from '../components/NexusConfigForm.vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import { apiUrl, connectorsUrl, jsonFetch } from '../services/api'
import { applyDensity, loadDensity, type Density } from '../services/preferences'

const density = ref<Density>(loadDensity())
function setDensity(value: Density) {
  density.value = value
  applyDensity(value)
}

// --- Obsidian vault sync (Phase D) --------------------------------------------
interface VaultStatus {
  vault_path: string
  write_enabled: boolean
  files: Record<string, number>
  conflicts: number
  last_run: { last_phase: string; at: string } | null
}

const vaultStatus = ref<VaultStatus | null>(null)
const vaultBusy = ref(false)
const vaultMessage = ref('')
const confirmEnable = ref(false)

const vaultFileSummary = computed(() =>
  vaultStatus.value
    ? Object.entries(vaultStatus.value.files).map(([k, v]) => `${v} ${k}`).join(', ') || 'none indexed yet'
    : '')

async function loadVaultStatus() {
  try {
    vaultStatus.value = await jsonFetch<VaultStatus>(`${connectorsUrl}/api/connectors/obsidian/sync/status`)
  } catch {
    vaultStatus.value = null // 409 = vault not configured; the hint text covers it
  }
}

async function validateVault() {
  vaultBusy.value = true
  vaultMessage.value = ''
  try {
    await jsonFetch(`${connectorsUrl}/api/connectors/obsidian/path/validate`, {
      method: 'POST',
      body: JSON.stringify({ relative_path: 'Notes/nexus-probe.md' }),
    })
    vaultMessage.value = 'Vault path is valid and contained.'
  } catch (err) {
    vaultMessage.value = err instanceof Error ? err.message : String(err)
  } finally {
    vaultBusy.value = false
  }
}

async function indexVault() {
  vaultBusy.value = true
  vaultMessage.value = ''
  try {
    const result = await jsonFetch<{ indexed: number; new_captures: number }>(
      `${connectorsUrl}/api/connectors/obsidian/sync/index`, { method: 'POST', body: '{}' })
    vaultMessage.value = `Indexed ${result.indexed} files (${result.new_captures} new captures from the vault).`
    await loadVaultStatus()
  } catch (err) {
    vaultMessage.value = err instanceof Error ? err.message : String(err)
  } finally {
    vaultBusy.value = false
  }
}

async function runVaultSync(execute: boolean) {
  vaultBusy.value = true
  vaultMessage.value = ''
  try {
    const result = await jsonFetch<{ outbound?: { mode: string; planned: number; written: number }; inbound?: { applied: number; conflicts: number } }>(
      `${connectorsUrl}/api/connectors/obsidian/sync/run`,
      { method: 'POST', body: JSON.stringify({ execute, direction: 'both' }) })
    const out = result.outbound
    const inb = result.inbound
    vaultMessage.value = `${out?.mode === 'write' ? 'Synced' : 'Dry-run'}: ${out?.planned ?? 0} planned, ${out?.written ?? 0} written, ${inb?.applied ?? 0} applied inbound, ${inb?.conflicts ?? 0} conflicts.`
    await loadVaultStatus()
  } catch (err) {
    vaultMessage.value = err instanceof Error ? err.message : String(err)
  } finally {
    vaultBusy.value = false
  }
}

async function enableVault() {
  vaultBusy.value = true
  try {
    const result = await jsonFetch<{ backup: string | null }>(
      `${connectorsUrl}/api/connectors/obsidian/sync/enable`,
      { method: 'POST', body: JSON.stringify({ enabled: true }) })
    vaultMessage.value = result.backup ? `Vault write enabled. Backup: ${result.backup}` : 'Vault write enabled.'
    await loadVaultStatus()
  } catch (err) {
    vaultMessage.value = err instanceof Error ? err.message : String(err)
  } finally {
    vaultBusy.value = false
  }
}

onMounted(loadVaultStatus)

const message = ref('')
const failed = ref(false)
const phoneNumber = ref(localStorage.getItem('settings_phone') || '')
const serviceStatus = ref<{ name: string; ok: boolean }[]>([])

const fields: ConfigField[] = [
  { key: 'GOOGLE_REDIRECT_URI', label: 'Google OAuth redirect URI', kind: 'url' },
  { key: 'MICROSOFT_REDIRECT_URI', label: 'Microsoft OAuth redirect URI', kind: 'url' },
  { key: 'TWILIO_AUTH_TOKEN', label: 'Twilio auth token', kind: 'text', secret: true },
  { key: 'TWILIO_WHATSAPP_FROM', label: 'Twilio WhatsApp sender', kind: 'whatsapp' },
  { key: 'AWS_SECRET_ACCESS_KEY', label: 'AWS secret access key', kind: 'text', secret: true },
  { key: 'AZURE_STORAGE_CONNECTION_STRING', label: 'Azure storage connection string', kind: 'text', secret: true },
]

async function save(values: Record<string, string>) {
  failed.value = false
  message.value = ''
    saveLocalSettingsSnapshot()
  try {
    for (const [key, value] of Object.entries(values)) {
      if (value && value !== '********') {
        await jsonFetch(`${apiUrl}/api/settings/${encodeURIComponent(key)}`, { method: 'PATCH', body: JSON.stringify({ value }) })
      }
    }
    if (phoneNumber.value) {
      localStorage.setItem('settings_phone', phoneNumber.value)
    }
    message.value = 'Configuration saved and validated. Restart the affected service to apply it.'
  } catch (error) {
    failed.value = true
    message.value = error instanceof Error ? error.message : String(error)
  }
}

async function checkServices() {
  const targets = [
    { name: 'api-gateway', url: `${apiUrl}/health` },
    { name: 'connector-service', url: `${apiUrl}/api/connectors/health` },
    { name: 'sync-engine', url: `${apiUrl}/api/sync/health` },
  ]
  serviceStatus.value = await Promise.all(
    targets.map(async (t) => {
      try {
        const res = await fetch(t.url)
        return { name: t.name, ok: res.ok }
      } catch {
        return { name: t.name, ok: false }
      }
    })
  )
}

const requiredRules = [
  (value: unknown) => Boolean(String(value ?? '').trim()) || 'Required'
]

// const serviceStatus = ref<Record<string, string>>({})

function saveLocalSettingsSnapshot() {
  localStorage.setItem('personal-os.settings.lastValidatedAt', new Date().toISOString())
}

// async function checkServices() {
//   serviceStatus.value = { api: 'checking' }
//   try {
//     const response = await fetch('/health')
//     serviceStatus.value = { api: response.ok ? 'ok' : 'failed' }
//   } catch {
//     serviceStatus.value = { api: 'failed' }
//   }
// }

</script>
