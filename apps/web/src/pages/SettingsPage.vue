<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="System" title="Settings" subtitle="Non-secret configuration for your Personal OS instance. Secrets must be set in .env or through the bootstrap wizard.">
      <template #actions>
        <q-btn color="primary" icon="mdi-content-save" label="Save" :loading="saving" @click="save" />
        <q-btn outline icon="mdi-refresh" label="Reload" @click="load" />
      </template>
    </NexusPageHero>

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ error }}
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <q-banner v-if="saved" class="bg-positive text-white" rounded>
      <template #avatar><q-icon name="mdi-check-circle-outline" /></template>
      Settings saved to local storage.
    </q-banner>

    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-6">
        <q-card class="glass-card">
          <q-card-section>
            <div class="text-h6 q-mb-sm">General</div>
            <div class="column q-gutter-md">
              <q-input v-model="config.instanceName" outlined label="Instance name" hint="Display name for this Personal OS instance" />
              <q-select v-model="config.theme" outlined :options="['dark', 'auto']" label="Theme" />
              <q-select v-model="config.defaultModule" outlined :options="moduleOptions" label="Default landing page" emit-value map-options />
            </div>
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-md-6">
        <q-card class="glass-card">
          <q-card-section>
            <div class="text-h6 q-mb-sm">Capture & Secretary</div>
            <div class="column q-gutter-md">
              <q-input v-model="config.secretaryEmail" outlined label="Secretary email" type="email" :rules="[v => !v || /.+@.+\..+/.test(v) || 'Invalid email']" />
              <q-input v-model="config.secretaryWhatsApp" outlined label="Secretary WhatsApp" hint="E.164 format: +1234567890" :rules="[v => !v || /^\+\d{8,15}$/.test(v) || 'Must be E.164 format']" />
              <q-toggle v-model="config.captureKeyboardShortcut" label="Ctrl+Enter to submit captures" />
            </div>
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-md-6">
        <q-card class="glass-card">
          <q-card-section>
            <div class="text-h6 q-mb-sm">Notifications</div>
            <div class="column q-gutter-md">
              <q-input v-model="config.ntfyTopic" outlined label="ntfy topic" hint="Private topic name for push notifications" />
              <q-toggle v-model="config.notifyOnCapture" label="Notify on capture" />
              <q-toggle v-model="config.notifyOnSync" label="Notify on sync conflict" />
            </div>
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-md-6">
        <q-card class="glass-card">
          <q-card-section>
            <div class="text-h6 q-mb-sm">Sync & Storage</div>
            <div class="column q-gutter-md">
              <q-select v-model="config.conflictStrategy" outlined :options="['field_merge', 'manual', 'last_write_wins']" label="Default conflict strategy" />
              <q-toggle v-model="config.offlineQueueEnabled" label="Enable offline mutation queue" />
              <q-input v-model.number="config.syncIntervalSeconds" outlined type="number" label="Sync interval (seconds)" :rules="[v => v >= 10 || 'Minimum 10 seconds']" />
            </div>
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-md-6">
        <q-card class="glass-card">
          <q-card-section>
            <div class="text-h6 q-mb-sm">Coding Agent</div>
            <div class="column q-gutter-md">
              <q-toggle v-model="config.codingAgentAutoApprove" label="Auto-approve jobs (skip manual step)" color="warning" />
              <q-input v-model="config.codingAgentRepoRoot" outlined label="Default repo root" hint="Leave blank to use server default" />
            </div>
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-md-6">
        <q-card class="glass-card">
          <q-card-section>
            <div class="text-h6 q-mb-sm">API Connection</div>
            <div class="column q-gutter-md">
              <q-input v-model="config.apiHost" outlined label="API host" hint="Usually localhost or your Tailscale IP" />
              <q-input v-model.number="config.apiPort" outlined type="number" label="API port" :rules="[v => (v >= 1 && v <= 65535) || 'Port 1-65535']" />
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Environment check</div>
        <p style="color:var(--nexus-muted);font-size:13px">Secrets must be set in <code>.env</code> — never in the UI. The following shows which services are reachable.</p>
      </q-card-section>
      <q-card-section v-if="serviceStatus">
        <q-list dense bordered separator class="rounded-borders">
          <q-item v-for="(val, key) in serviceStatus" :key="key">
            <q-item-section>{{ key }}</q-item-section>
            <q-item-section side>
              <q-badge :color="val ? 'positive' : 'grey'" :label="val ? 'reachable' : 'unreachable'" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import { apiUrl, connectorsUrl, syncUrl, captureUrl, jsonFetch } from '../services/api'

const STORAGE_KEY = 'nexus-settings'

const moduleOptions = [
  { label: 'Command Center', value: '/' },
  { label: 'Capture', value: '/capture' },
  { label: 'Tasks', value: '/tasks' },
  { label: 'Study Companion', value: '/study-companion' },
]

const config = reactive({
  instanceName: 'Personal OS',
  theme: 'dark',
  defaultModule: '/',
  secretaryEmail: '',
  secretaryWhatsApp: '',
  captureKeyboardShortcut: true,
  ntfyTopic: '',
  notifyOnCapture: false,
  notifyOnSync: true,
  conflictStrategy: 'field_merge',
  offlineQueueEnabled: true,
  syncIntervalSeconds: 30,
  codingAgentAutoApprove: false,
  codingAgentRepoRoot: '',
  apiHost: 'localhost',
  apiPort: 8080,
})

const saving = ref(false)
const saved = ref(false)
const error = ref('')
const serviceStatus = ref<Record<string, boolean> | null>(null)

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) Object.assign(config, JSON.parse(raw))
  } catch {}
  checkServices()
}

function save() {
  saving.value = true
  saved.value = false
  error.value = ''
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
    saved.value = true
    setTimeout(() => { saved.value = false }, 3000)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    saving.value = false
  }
}

async function checkServices() {
  const checks: Record<string, string> = {
    'API Gateway': `${apiUrl}/health`,
    'Capture': `${captureUrl}/health`,
    'Connectors': `${connectorsUrl}/health`,
    'Sync': `${syncUrl}/health`,
  }
  const results: Record<string, boolean> = {}
  await Promise.all(
    Object.entries(checks).map(async ([name, url]) => {
      try {
        await jsonFetch(url)
        results[name] = true
      } catch {
        results[name] = false
      }
    })
  )
  serviceStatus.value = results
}

onMounted(load)
</script>
