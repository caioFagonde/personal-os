<template>
  <q-page class="column q-gutter-lg">

    <NexusPageHero eyebrow="OAuth · Messaging · Mesh" title="Connectors" subtitle="One-click provider onboarding. Google and Microsoft open a consent window; device-code provides a QR/code fallback. Refresh credentials are encrypted server-side.">
      <template #actions>
        <q-btn color="primary" icon="mdi-refresh" label="Refresh status" :loading="refreshing" @click="load" />
        <q-btn outline color="primary" icon="mdi-cellphone-key" label="What is device-code?" @click="showDeviceHelp = !showDeviceHelp" />
      </template>
    </NexusPageHero>

    <q-banner v-if="loadError" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ loadError }}
    </q-banner>

    <q-card class="glass-card" v-if="showDeviceHelp">
      <q-card-section>
        <div class="text-h6 q-mb-xs">Device-code login</div>
        <p>Use device-code login when the callback redirect cannot reach this machine (e.g., phone, corporate network, or firewall). You will see a short user-code and a URL to open on any browser. No manual token copying needed — Personal OS polls until you complete consent.</p>
      </q-card-section>
    </q-card>

    <!-- Provider cards -->
    <div class="action-grid">
      <q-card v-for="item in connectors" :key="item.id" class="glass-card quick-card">
        <q-card-section>
          <div class="row items-start justify-between no-wrap q-mb-xs">
            <div class="text-h6 text-capitalize">{{ item.id }}</div>
            <q-badge :color="badgeColor(item)" :label="item.status" />
          </div>
          <p style="color:var(--nexus-muted);font-size:13px;margin:0 0 10px">{{ item.message }}</p>

          <!-- OAuth setup instructions when not configured -->
          <q-expansion-item
            v-if="(item.id === 'google' || item.id === 'microsoft') && !item.configured"
            icon="mdi-cog-outline"
            label="Setup instructions"
            header-class="text-accent"
            dense
          >
            <div class="q-pa-sm text-caption" style="color:var(--nexus-muted)">
              <p>Add the following to your <code>.env</code> and restart <code>connector-service</code>:</p>
              <pre class="code-block" v-if="item.id === 'google'">GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8080/api/proxy/connectors/api/connectors/google/callback</pre>
              <pre class="code-block" v-if="item.id === 'microsoft'">MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
MICROSOFT_TENANT=common
MICROSOFT_REDIRECT_URI=http://localhost:8080/api/proxy/connectors/api/connectors/microsoft/callback</pre>
              <p>Register the redirect URI above in your OAuth app console, then run:</p>
              <pre class="code-block">docker compose --env-file .env restart connector-service</pre>
            </div>
          </q-expansion-item>

          <q-expansion-item
            v-if="['obsidian', 'notion', 'trello'].includes(item.id)"
            icon="mdi-cog-outline"
            label="Setup contract"
            header-class="text-accent"
            dense
          >
            <div class="q-pa-sm text-caption" style="color:var(--nexus-muted)">
              <p>Configure these fields on the connector service. Secret values stay server-side and are never stored in browser localStorage.</p>
              <q-list dense>
                <q-item v-for="field in item.config_metadata || []" :key="field.key">
                  <q-item-section>
                    <q-item-label><code>{{ field.key }}</code></q-item-label>
                    <q-item-label caption>{{ field.label }} · {{ field.required ? 'required' : 'optional' }}{{ field.secret ? ' · secret' : '' }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
              <p v-if="item.id === 'obsidian'">Exports use relative <code>.md</code> or <code>.markdown</code> paths and are contained inside the configured vault. Markdown links, tags, YAML frontmatter, and timestamp-based Zettelkasten filenames remain compatible.</p>
              <p v-else>Marketplace actions are dry-run only and do not call the external provider.</p>
            </div>
          </q-expansion-item>

          <!-- ntfy subscription help -->
          <q-expansion-item
            v-if="item.id === 'ntfy'"
            icon="mdi-bell-outline"
            label="Mobile subscription"
            header-class="text-accent"
            dense
          >
            <div class="q-pa-sm text-caption" style="color:var(--nexus-muted)">
              <p>Install ntfy on your phone (<a href="https://ntfy.sh" target="_blank" rel="noopener">ntfy.sh</a>), then subscribe to the topic configured in <code>NTFY_TOPIC</code>. The base URL is in <code>NTFY_BASE_URL</code>.</p>
              <p>If you are running a private ntfy server, use your Tailscale IP as the base URL so the phone can reach it over the mesh.</p>
            </div>
          </q-expansion-item>

          <!-- Tailscale details -->
          <div v-if="item.id === 'tailscale' && tailscaleDetail">
            <q-list dense class="q-mt-xs">
              <q-item v-if="tailscaleDetail.hostname">
                <q-item-section>Hostname</q-item-section>
                <q-item-section side class="text-muted">{{ tailscaleDetail.hostname }}</q-item-section>
              </q-item>
              <q-item v-if="tailscaleDetail.ip">
                <q-item-section>Tailscale IP</q-item-section>
                <q-item-section side class="text-accent text-weight-bold">{{ tailscaleDetail.ip }}</q-item-section>
              </q-item>
            </q-list>
          </div>
        </q-card-section>

        <q-card-actions align="between">
          <div class="row q-gutter-xs">
            <q-btn
              v-if="item.id === 'google' || item.id === 'microsoft'"
              color="primary"
              unelevated
              size="sm"
              :disable="!item.configured"
              :label="item.configured ? 'Connect' : 'Configure .env first'"
              @click="authorize(item.id)"
            />
            <q-btn
              v-if="(item.id === 'google' || item.id === 'microsoft') && item.configured"
              outline
              color="primary"
              size="sm"
              label="Device code"
              @click="startDeviceFlow(item.id)"
            />
            <q-btn v-if="item.id === 'twilio'" outline color="primary" size="sm" label="Dry-run test" @click="testTwilio" />
            <q-btn v-if="item.id === 'ntfy'" outline color="primary" size="sm" label="Dry-run test" @click="testNtfy" />
            <q-btn v-if="item.id === 'tailscale'" outline color="primary" size="sm" label="Check status" @click="checkTailscale" />
            <q-btn v-if="item.id === 'obsidian'" outline color="primary" size="sm" label="Export dry-run" @click="dryRunObsidianExport" />
            <q-btn v-if="item.id === 'obsidian'" flat color="primary" size="sm" label="Import dry-run" @click="dryRunObsidianImport" />
            <q-btn v-if="item.id === 'notion'" outline color="primary" size="sm" label="Page dry-run" @click="dryRunNotionPage" />
            <q-btn v-if="item.id === 'trello'" outline color="primary" size="sm" label="Card dry-run" @click="dryRunTrelloCard" />
          </div>
        </q-card-actions>
      </q-card>
    </div>

    <!-- Device-code flow panel -->
    <q-card v-if="deviceFlow" class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">{{ deviceFlow.provider }} device-code login</div>
        <p>Open the link below, enter the code, approve access, then click Poll.</p>
        <div class="row items-center q-gutter-md q-mb-md">
          <div class="text-h3 text-primary text-weight-bold">{{ deviceFlow.user_code }}</div>
          <div>
            <q-btn color="primary" unelevated :href="deviceFlow.verification_uri_complete || deviceFlow.verification_uri" target="_blank" rel="noopener" icon="mdi-open-in-new" label="Open verification page" />
          </div>
        </div>
        <div class="row q-gutter-sm">
          <q-btn outline color="primary" icon="mdi-refresh" label="Poll for token" @click="pollDeviceFlow" />
          <q-btn flat color="grey" label="Cancel" @click="deviceFlow = null" />
        </div>
      </q-card-section>
    </q-card>

    <!-- Result panel — shown only when non-empty and actionable -->
    <q-card class="glass-card" v-if="result">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Result</div>
        <div v-if="resultIsText">{{ result }}</div>
        <div v-else>
          <div v-if="resultObj.status" class="q-mb-sm">
            <q-badge :color="resultObj.status === 'connected' ? 'positive' : resultObj.status === 'dry_run' ? 'info' : 'warning'" :label="resultObj.status" class="q-mr-xs" />
            <span v-if="resultObj.provider" class="text-muted">{{ resultObj.provider }}</span>
          </div>
          <div v-if="resultObj.message" class="q-mb-sm">{{ resultObj.message }}</div>
          <div v-if="resultObj.topic" class="q-mb-sm">Topic: <code>{{ resultObj.topic }}</code></div>
          <div v-if="resultObj.ip" class="q-mb-sm">IP: <strong class="text-accent">{{ resultObj.ip }}</strong></div>
          <div v-if="resultObj.hostname" class="q-mb-sm">Hostname: {{ resultObj.hostname }}</div>
          <div v-if="resultObj.scopes" class="q-mb-sm">Scopes: {{ Array.isArray(resultObj.scopes) ? resultObj.scopes.join(', ') : resultObj.scopes }}</div>
          <pre class="code-block q-mt-sm" v-if="showRaw">{{ JSON.stringify(resultObj, null, 2) }}</pre>
          <q-btn flat size="sm" :label="showRaw ? 'Hide raw' : 'Show raw JSON'" @click="showRaw = !showRaw" />
        </div>
      </q-card-section>
    </q-card>

  </q-page>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import { connectorsUrl, jsonFetch } from '../services/api'

type ConfigMetadata = { key: string; label: string; required: boolean; secret: boolean }
type Connector = { id: string; configured: boolean; status: string; message: string; config_metadata?: ConfigMetadata[] }
const connectors = ref<Connector[]>([])
const result = ref<string | null>(null)
const deviceFlow = ref<any | null>(null)
const loadError = ref('')
const refreshing = ref(false)
const showDeviceHelp = ref(false)
const showRaw = ref(false)
const tailscaleDetail = ref<any>(null)

const resultIsText = computed(() => typeof result.value === 'string' && !result.value.startsWith('{'))
const resultObj = computed(() => {
  if (!result.value || resultIsText.value) return {}
  try { return JSON.parse(result.value) } catch { return {} }
})

function badgeColor(item: Connector): string {
  if (item.configured && (item.status === 'connected' || item.status === 'configured')) return 'positive'
  if (item.configured) return 'info'
  return 'warning'
}

async function load() {
  refreshing.value = true
  loadError.value = ''
  try {
    const data = await jsonFetch<{ connectors: Connector[] }>(`${connectorsUrl}/api/connectors`)
    connectors.value = data.connectors
  } catch (error) {
    loadError.value = describeConnectorError(error)
  } finally {
    refreshing.value = false
  }
}

function describeConnectorError(error: unknown): string {
  if (!(error instanceof Error)) return String(error)
  try {
    const jsonStart = error.message.indexOf('{')
    if (jsonStart >= 0) {
      const payload = JSON.parse(error.message.slice(jsonStart))
      const detail = payload.detail ?? payload.error ?? payload
      if (detail.required_env) return `${detail.message}\n\nRequired: ${detail.required_env.join(', ')}`
      if (detail.missing_config) return `${detail.message}\n\nMissing: ${detail.missing_config.join(', ')}`
      if (detail.message) return detail.message
    }
  } catch {}
  return error.message
}

async function authorize(provider: string) {
  result.value = null
  try {
    const data = await jsonFetch<{ authorization_url: string }>(`${connectorsUrl}/api/connectors/${provider}/start`)
    window.open(data.authorization_url, '_blank', 'noopener,noreferrer')
    result.value = JSON.stringify({ status: 'browser_opened', message: `Complete ${provider} consent in the new tab, then refresh status.` })
  } catch (error) {
    result.value = describeConnectorError(error)
  }
}

async function startDeviceFlow(provider: string) {
  result.value = null
  try {
    deviceFlow.value = await jsonFetch<any>(`${connectorsUrl}/api/connectors/${provider}/device/start`)
  } catch (error) {
    result.value = describeConnectorError(error)
  }
}

async function pollDeviceFlow() {
  if (!deviceFlow.value) return
  try {
    const data = await jsonFetch<any>(`${connectorsUrl}/api/connectors/${deviceFlow.value.provider}/device/poll`, {
      method: 'POST',
      body: JSON.stringify({ device_code: deviceFlow.value.device_code }),
    })
    result.value = JSON.stringify(data)
    if (data.status === 'connected') { deviceFlow.value = null; await load() }
  } catch (error) {
    result.value = describeConnectorError(error)
  }
}

async function testTwilio() {
  result.value = null
  try {
    const data = await jsonFetch<any>(`${connectorsUrl}/api/connectors/twilio/test`, { method: 'POST', body: JSON.stringify({ execute: false }) })
    result.value = JSON.stringify(data)
  } catch (error) { result.value = describeConnectorError(error) }
}

async function testNtfy() {
  result.value = null
  try {
    const data = await jsonFetch<any>(`${connectorsUrl}/api/connectors/ntfy/test`, { method: 'POST', body: JSON.stringify({ execute: false }) })
    result.value = JSON.stringify(data)
  } catch (error) { result.value = describeConnectorError(error) }
}

async function checkTailscale() {
  result.value = null
  try {
    const data = await jsonFetch<any>(`${connectorsUrl}/api/connectors/tailscale/status`)
    tailscaleDetail.value = data
    result.value = JSON.stringify(data)
  } catch (error) { result.value = describeConnectorError(error) }
}

async function runDryRun(path: string, payload: Record<string, unknown>) {
  result.value = null
  try {
    const data = await jsonFetch<any>(`${connectorsUrl}${path}`, {
      method: 'POST',
      body: JSON.stringify({ ...payload, execute: false }),
    })
    result.value = JSON.stringify(data)
  } catch (error) {
    result.value = describeConnectorError(error)
  }
}

const dryRunObsidianExport = () => runDryRun('/api/connectors/obsidian/export', {
  relative_path: 'Zettelkasten/202606081200 Personal OS export.md',
  content: '# Personal OS export\n\nDry-run preview.',
})
const dryRunObsidianImport = () => runDryRun('/api/connectors/obsidian/import', {
  relative_path: 'Zettelkasten/202606081200 Personal OS import.md',
})
const dryRunNotionPage = () => runDryRun('/api/connectors/notion/pages/dry-run', {
  title: 'Personal OS dry-run page',
  content: 'No external page will be created.',
})
const dryRunTrelloCard = () => runDryRun('/api/connectors/trello/cards/dry-run', {
  title: 'Personal OS dry-run card',
  description: 'No external card will be created.',
  labels: [],
})

onMounted(load)
</script>
