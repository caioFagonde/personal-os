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
import { ref } from 'vue'
import NexusConfigForm, { type ConfigField } from '../components/NexusConfigForm.vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import { apiUrl, jsonFetch } from '../services/api'

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

const serviceStatus = ref<Record<string, string>>({})

function saveLocalSettingsSnapshot() {
  localStorage.setItem('personal-os.settings.lastValidatedAt', new Date().toISOString())
}

async function checkServices() {
  serviceStatus.value = { api: 'checking' }
  try {
    const response = await fetch('/health')
    serviceStatus.value = { api: response.ok ? 'ok' : 'failed' }
  } catch {
    serviceStatus.value = { api: 'failed' }
  }
}

</script>
