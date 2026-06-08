<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Setup" title="Settings" subtitle="Validate connector and cloud configuration before restarting services." />
    <q-banner v-if="message" :class="failed ? 'bg-negative text-white' : 'bg-positive text-white'" rounded>{{ message }}</q-banner>
    <q-card class="glass-card">
      <q-card-section><div class="text-h6">Provider configuration</div></q-card-section>
      <q-card-section><NexusConfigForm :fields="fields" @save="save" /></q-card-section>
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
  try {
    for (const [key, value] of Object.entries(values)) {
      if (value && value !== '********') {
        await jsonFetch(`${apiUrl}/api/settings/${encodeURIComponent(key)}`, { method: 'PATCH', body: JSON.stringify({ value }) })
      }
    }
    message.value = 'Configuration saved and validated. Restart the affected service to apply it.'
  } catch (error) {
    failed.value = true
    message.value = error instanceof Error ? error.message : String(error)
  }
}
</script>
