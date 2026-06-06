<template>
  <q-page class="q-pa-md column q-gutter-md">
    <section class="hero-panel">
      <div class="eyebrow">Phase 10</div>
      <h1>Connector Onboarding</h1>
      <p>Connect Google, Microsoft, Twilio WhatsApp, ntfy, Tailscale, backup, and device pairing. Missing consent opens the correct authorization path; durable credentials are stored server-side after approval.</p>
      <q-btn color="primary" icon="mdi-refresh" label="Refresh status" @click="load" />
    </section>

    <div class="row q-col-gutter-md">
      <div v-for="item in connectors" :key="item.id" class="col-12 col-md-6 col-lg-4">
        <q-card class="glass-card full-height">
          <q-card-section>
            <div class="text-h6 text-capitalize">{{ item.id }}</div>
            <q-badge :color="item.configured ? 'positive' : 'warning'" :label="item.status" />
            <p class="q-mt-sm">{{ item.message }}</p>
          </q-card-section>
          <q-card-actions>
            <q-btn v-if="item.id === 'google' || item.id === 'microsoft'" outline color="primary" label="Authorize" @click="authorize(item.id)" />
            <q-btn v-if="item.id === 'twilio'" outline color="primary" label="Dry-run Twilio" @click="testTwilio" />
            <q-btn v-if="item.id === 'ntfy'" outline color="primary" label="Dry-run ntfy" @click="testNtfy" />
            <q-btn v-if="item.id === 'tailscale'" outline color="primary" label="Check mesh" @click="checkTailscale" />
          </q-card-actions>
        </q-card>
      </div>
    </div>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6">Connector test result</div>
        <pre>{{ result }}</pre>
      </q-card-section>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { connectorsUrl, jsonFetch } from '../services/api'

type Connector = { id: string; configured: boolean; status: string; message: string }
const connectors = ref<Connector[]>([])
const result = ref('No test run yet.')
async function load() {
  const data = await jsonFetch<{ connectors: Connector[] }>(`${connectorsUrl}/api/connectors`)
  connectors.value = data.connectors
}
async function authorize(provider: string) {
  const data = await jsonFetch<{ authorization_url: string }>(`${connectorsUrl}/api/connectors/${provider}/start`)
  window.open(data.authorization_url, '_blank', 'noopener,noreferrer')
  result.value = `Opened ${provider} authorization window. Complete consent, then refresh.`
}
async function testTwilio() { result.value = JSON.stringify(await jsonFetch(`${connectorsUrl}/api/connectors/twilio/test`, { method: 'POST', body: JSON.stringify({ execute: false }) }), null, 2) }
async function testNtfy() { result.value = JSON.stringify(await jsonFetch(`${connectorsUrl}/api/connectors/ntfy/test`, { method: 'POST', body: JSON.stringify({ execute: false }) }), null, 2) }
async function checkTailscale() { result.value = JSON.stringify(await jsonFetch(`${connectorsUrl}/api/connectors/tailscale/status`), null, 2) }
onMounted(load)
</script>
