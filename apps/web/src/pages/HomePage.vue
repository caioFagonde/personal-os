<template>
  <q-page padding>
    <h1>Nexus Core</h1>
    <p>Control plane shell for specialized local-first modules.</p>
    <q-btn label="Load modules" @click="load" />
    <pre>{{ modules }}</pre>
  </q-page>
</template>
<script setup lang="ts">
import { ref } from 'vue'
const modules = ref([])
async function load() {
  const api = import.meta.env.VITE_API_URL || 'http://localhost:8080'
  modules.value = await fetch(`${api}/api/modules`).then(r => r.json())
}
</script>
