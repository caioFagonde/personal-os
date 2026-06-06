<template>
  <q-page class="q-pa-md column q-gutter-md">
    <section class="hero-panel"><h1>Sync Health</h1><p>Control-plane health, connector readiness, sync conflicts, and continuity status.</p></section>
    <q-btn color="primary" icon="mdi-heart-pulse" label="Run health check" @click="load" />
    <pre>{{ data }}</pre>
  </q-page>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { apiUrl, connectorsUrl, jsonFetch } from '../services/api'
const data = ref('')
async function load() {
  const health = await jsonFetch(`${apiUrl}/api/control/health`)
  const connectors = await jsonFetch(`${connectorsUrl}/api/connectors/status`)
  data.value = JSON.stringify({ health, connectors }, null, 2)
}
</script>
