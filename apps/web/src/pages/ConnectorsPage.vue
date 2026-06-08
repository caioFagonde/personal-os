<template>
  <q-page class="column q-gutter-lg">

    <NexusPageHero
      eyebrow="Marketplace"
      title="Connector Marketplace"
      subtitle="Install, configure, and connect providers. OAuth, messaging, infrastructure, AI models, and cloud — all in one place."
    >
      <template #actions>
        <q-btn color="primary" icon="mdi-refresh" label="Refresh status" :loading="refreshing" @click="load" />
        <q-btn outline color="primary" icon="mdi-cellphone-key" label="Device-code login" @click="showDeviceHelp = !showDeviceHelp" />
      </template>
    </NexusPageHero>

    <NexusErrorBanner v-if="loadError" :error="loadError" @dismiss="loadError = ''" />

    <!-- Summary metrics -->
    <div class="row q-gutter-sm">
      <MetricCard label="Connected" :value="connectedCount" />
      <MetricCard label="Needs config" :value="needsConfigCount" />
      <MetricCard label="Total" :value="allProviders.length" />
    </div>

    <!-- Filter bar -->
    <div class="row items-center q-gutter-sm q-mb-sm" style="flex-wrap:wrap">
      <q-input
        v-model="searchQuery"
        outlined
        dense
        clearable
        placeholder="Search providers..."
        style="min-width:220px;max-width:360px"
      >
        <template #prepend><q-icon name="mdi-magnify" /></template>
      </q-input>
      <q-btn-toggle
        v-model="filterState"
        no-caps
        rounded
        unelevated
        toggle-color="primary"
        :options="stateFilterOptions"
        class="filter-toggle"
      />
    </div>

    <!-- Device-code help card -->
    <q-card class="glass-card" v-if="showDeviceHelp">
      <q-card-section>
        <div class="text-h6 q-mb-xs">Device-code login</div>
        <p>Use device-code login when the callback redirect cannot reach this machine (e.g., phone, corporate network, or firewall). You will see a short user-code and a URL to open on any browser. No manual token copying needed — Personal OS polls until you complete consent.</p>
      </q-card-section>
    </q-card>

    <!-- Provider cards by category -->
    <template v-for="(cat, catKey) in categoryGroups" :key="catKey">
      <div v-if="cat.providers.length" class="q-mt-md">
        <div class="section-heading q-mb-sm">
          <q-icon :name="cat.icon" size="16px" class="q-mr-xs" />
          {{ cat.label }} ({{ cat.providers.length }})
        </div>
        <div class="action-grid">
          <ProviderCard
            v-for="item in cat.providers"
            :key="item.manifest.id"
            :manifest="item.manifest"
            :status="item.status"
          >
            <template #actions="{ status: st, manifest: mf }">
              <!-- OAuth providers: Connect / Device code -->
              <template v-if="mf.id === 'google' || mf.id === 'microsoft'">
                <q-btn
                  color="primary"
                  unelevated
                  size="sm"
                  :disable="!st.configured"
                  :label="st.configured ? 'Connect' : 'Configure .env first'"
                  @click="authorize(mf.id)"
                />
                <q-btn
                  v-if="st.configured"
                  outline
                  color="primary"
                  size="sm"
                  label="Device code"
                  @click="startDeviceFlow(mf.id)"
                />
              </template>
              <!-- Twilio: dry-run test -->
              <q-btn v-if="mf.id === 'twilio'" outline color="primary" size="sm" label="Dry-run test" @click="testTwilio" />
              <!-- ntfy: dry-run test -->
              <q-btn v-if="mf.id === 'ntfy'" outline color="primary" size="sm" label="Dry-run test" @click="testNtfy" />
              <!-- Tailscale: check status -->
              <q-btn v-if="mf.id === 'tailscale'" outline color="primary" size="sm" label="Check status" @click="checkTailscale" />
              <!-- Cloud providers: dry-run plan badge -->
              <q-badge v-if="mf.cloudSafetyNote" color="warning" label="Dry-run plan only" />
            </template>
          </ProviderCard>
        </div>
      </div>
    </template>

    <NexusEmptyState
      v-if="filteredProviders.length === 0 && !refreshing"
      icon="mdi-magnify"
      message="No providers match your filter."
      hint="Try adjusting the search or filter settings."
    />

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

    <!-- Result panel -->
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
import NexusErrorBanner from '../components/NexusErrorBanner.vue'
import NexusEmptyState from '../components/NexusEmptyState.vue'
import MetricCard from '../components/MetricCard.vue'
import ProviderCard from '../components/ProviderCard.vue'
import { connectorsUrl, jsonFetch } from '../services/api'
import {
  type ProviderManifest,
  type ProviderLiveStatus,
  type ProviderCategory,
  PROVIDER_MANIFESTS,
  PROVIDER_CATEGORIES,
  deriveProviderState,
} from '../providers/manifests'

type BackendConnector = { id: string; configured: boolean; status: string; message: string }
interface ProviderEntry { manifest: ProviderManifest; status: ProviderLiveStatus }

const backendConnectors = ref<BackendConnector[]>([])
const result = ref<string | null>(null)
const deviceFlow = ref<any | null>(null)
const loadError = ref('')
const refreshing = ref(false)
const showDeviceHelp = ref(false)
const showRaw = ref(false)
const searchQuery = ref('')
const filterState = ref('all')

const stateFilterOptions = [
  { label: 'All', value: 'all' },
  { label: 'Connected', value: 'connected' },
  { label: 'Needs setup', value: 'needs_setup' },
  { label: 'Cloud', value: 'cloud' },
]

const resultIsText = computed(() => typeof result.value === 'string' && !result.value.startsWith('{'))
const resultObj = computed(() => {
  if (!result.value || resultIsText.value) return {} as Record<string, any>
  try { return JSON.parse(result.value) } catch { return {} as Record<string, any> }
})

const allProviders = computed<ProviderEntry[]>(() => {
  const backendMap = new Map<string, BackendConnector>()
  for (const c of backendConnectors.value) backendMap.set(c.id, c)
  return PROVIDER_MANIFESTS.map(manifest => ({
    manifest,
    status: deriveProviderState(manifest, backendMap.get(manifest.id)),
  }))
})

const filteredProviders = computed<ProviderEntry[]>(() => {
  let list = allProviders.value
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(p =>
      p.manifest.name.toLowerCase().includes(q) ||
      p.manifest.description.toLowerCase().includes(q) ||
      p.manifest.capabilities.some(c => c.toLowerCase().includes(q))
    )
  }
  if (filterState.value === 'connected') {
    list = list.filter(p => p.status.state === 'connected')
  } else if (filterState.value === 'needs_setup') {
    list = list.filter(p => p.status.state !== 'connected' && p.status.state !== 'not_installed')
  } else if (filterState.value === 'cloud') {
    list = list.filter(p => p.manifest.category === 'cloud_providers')
  }
  return list
})

const connectedCount = computed(() => allProviders.value.filter(p => p.status.state === 'connected').length)
const needsConfigCount = computed(() => allProviders.value.filter(p => ['needs_config', 'malformed_config', 'ready_to_authorize'].includes(p.status.state)).length)

const categoryGroups = computed(() => {
  const filtered = new Set(filteredProviders.value.map(p => p.manifest.id))
  const result: Record<string, { label: string; icon: string; providers: ProviderEntry[] }> = {}
  for (const [catKey, catMeta] of Object.entries(PROVIDER_CATEGORIES)) {
    const providers = allProviders.value.filter(
      p => p.manifest.category === catKey as ProviderCategory && filtered.has(p.manifest.id)
    )
    result[catKey] = { ...catMeta, providers }
  }
  return result
})

function describeConnectorError(error: unknown): string {
  if (!(error instanceof Error)) return String(error)
  try {
    const jsonStart = error.message.indexOf('{')
    if (jsonStart >= 0) {
      const payload = JSON.parse(error.message.slice(jsonStart))
      const detail = payload.detail ?? payload
      if (detail.required_env) return `${detail.message}\n\nRequired: ${detail.required_env.join(', ')}`
      if (detail.message) return detail.message
    }
  } catch { /* use raw message */ }
  return error.message
}

async function load() {
  refreshing.value = true
  loadError.value = ''
  try {
    const data = await jsonFetch<{ connectors: BackendConnector[] }>(`${connectorsUrl}/api/connectors`)
    backendConnectors.value = data.connectors
  } catch (error) {
    loadError.value = describeConnectorError(error)
  } finally {
    refreshing.value = false
  }
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
    result.value = JSON.stringify(data)
  } catch (error) { result.value = describeConnectorError(error) }
}

onMounted(load)
</script>

<style scoped>
.filter-toggle {
  flex-wrap: wrap;
}
</style>
