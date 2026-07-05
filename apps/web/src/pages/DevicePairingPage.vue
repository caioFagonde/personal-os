<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Clone-and-continue" title="Device Pairing" subtitle="Create a short-lived pairing URL and QR code for phones, tablets, or a second PC." />

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ error }}
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <q-btn color="primary" icon="mdi-qrcode" label="Create pairing code" :loading="creating" @click="create" />

    <q-card v-if="pairing" class="glass-card">
      <q-card-section class="row q-col-gutter-lg items-center">
        <div class="col-12 col-md-4">
          <img :src="qrUrl" alt="Pairing QR code" class="pairing-qr" />
        </div>
        <div class="col-12 col-md-8">
          <div class="text-h6">Pairing URL</div>
          <q-input readonly :model-value="pairing.url" class="q-my-sm">
            <template #append><q-btn flat icon="mdi-content-copy" @click="copy(pairing.url)" /></template>
          </q-input>
          <q-input readonly label="Pairing code" :model-value="pairing.pairing_code">
            <template #append><q-btn flat icon="mdi-content-copy" @click="copy(pairing.pairing_code)" /></template>
          </q-input>
          <p class="text-caption q-mt-md">
            Expires in {{ pairing.expires_in_seconds }} seconds. Approve only devices you physically control.
          </p>
        </div>
      </q-card-section>
    </q-card>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-xs">This is the new device</div>
        <p class="text-caption">
          When AUTH_REQUIRED=true, new devices must present a pairing code minted on an
          already-trusted device. Enter it here, then register. The code is single-use,
          expires in 15 minutes, and is held only for this browser session.
        </p>
        <div class="row q-gutter-sm items-center">
          <q-input v-model="enteredCode" dense outlined label="Pairing code" style="min-width:220px" />
          <q-btn color="primary" unelevated label="Register this device" :loading="registering" @click="registerWithCode" />
        </div>
        <div v-if="registerResult" class="q-mt-sm">{{ registerResult }}</div>
      </q-card-section>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import { apiUrl, connectorsUrl, jsonFetch } from '../services/api'
import { registerDevice, setPairingCode } from '../services/auth'

const pairing = ref<any | null>(null)
const error = ref('')
const creating = ref(false)
const enteredCode = ref('')
const registering = ref(false)
const registerResult = ref('')
const qrUrl = computed(() =>
  pairing.value ? `${connectorsUrl}/api/connectors/device-pairing/qr?url=${encodeURIComponent(pairing.value.url)}` : ''
)

async function registerWithCode() {
  registering.value = true
  registerResult.value = ''
  error.value = ''
  try {
    if (enteredCode.value.trim()) setPairingCode(enteredCode.value)
    await registerDevice(apiUrl)
    registerResult.value = 'Device registered and paired. You can close this page.'
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    registering.value = false
  }
}

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

async function copy(value: string) {
  try {
    await navigator.clipboard?.writeText(value)
  } catch { /* clipboard not available in some contexts */ }
}
</script>
<style scoped>
.pairing-qr {
  width: 100%;
  max-width: 260px;
  background: white;
  border-radius: 18px;
  padding: 14px;
}
</style>
