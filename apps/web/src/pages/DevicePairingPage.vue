<template>
  <q-page class="q-pa-md column q-gutter-md">
    <section class="hero-panel">
      <div class="eyebrow">Clone-and-continue</div>
      <h1>Device Pairing</h1>
      <p>Create a short-lived pairing URL and QR code for phones, tablets, or a second PC.</p>
      <q-btn color="primary" icon="mdi-qrcode" label="Create pairing code" @click="create" />
    </section>
    <q-card v-if="pairing" class="glass-card">
      <q-card-section class="row q-col-gutter-lg items-center">
        <div class="col-12 col-md-4">
          <img :src="qrUrl" alt="Pairing QR code" class="pairing-qr" />
        </div>
        <div class="col-12 col-md-8">
          <div class="text-h6">Pairing URL</div>
          <q-input readonly :model-value="pairing.url" class="q-my-sm"><template #append><q-btn flat icon="mdi-content-copy" @click="copy(pairing.url)" /></template></q-input>
          <q-input readonly label="Pairing code" :model-value="pairing.pairing_code"><template #append><q-btn flat icon="mdi-content-copy" @click="copy(pairing.pairing_code)" /></template></q-input>
          <p class="text-caption q-mt-md">Expires in {{ pairing.expires_in_seconds }} seconds. Approve only devices you physically control.</p>
        </div>
      </q-card-section>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { connectorsUrl, jsonFetch } from '../services/api'
const pairing = ref<any | null>(null)
const qrUrl = computed(() => pairing.value ? `${connectorsUrl}/api/connectors/device-pairing/qr?url=${encodeURIComponent(pairing.value.url)}` : '')
async function create() { pairing.value = await jsonFetch(`${connectorsUrl}/api/connectors/device-pairing`, { method: 'POST', body: JSON.stringify({}) }) }
async function copy(value: string) { await navigator.clipboard?.writeText(value) }
</script>
<style scoped>.pairing-qr{width:100%;max-width:260px;background:white;border-radius:18px;padding:14px}</style>
