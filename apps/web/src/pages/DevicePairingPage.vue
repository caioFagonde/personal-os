<template>
  <q-page class="q-pa-md column q-gutter-md">
    <section class="hero-panel"><h1>Device Pairing</h1><p>Create a short-lived pairing URL for phones, tablets, or a second PC.</p></section>
    <q-btn color="primary" icon="mdi-qrcode" label="Create pairing code" @click="create" />
    <q-card v-if="pairing" class="glass-card"><q-card-section><div class="text-h6">Pairing URL</div><code>{{ pairing.url }}</code><p>Code: {{ pairing.pairing_code }}</p></q-card-section></q-card>
  </q-page>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { connectorsUrl, jsonFetch } from '../services/api'
const pairing = ref<any | null>(null)
async function create() { pairing.value = await jsonFetch(`${connectorsUrl}/api/connectors/device-pairing`, { method: 'POST', body: JSON.stringify({}) }) }
</script>
