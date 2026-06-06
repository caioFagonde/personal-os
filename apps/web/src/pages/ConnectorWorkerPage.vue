<template>
  <q-page class="column q-gutter-lg">
    <section class="hero-panel">
      <div class="eyebrow">Phase 11 Operations</div>
      <h1>Connector Worker</h1>
      <p>Drain WhatsApp, email, ntfy, automation, and backup delivery queues with auditable status.</p>
      <div class="row q-gutter-sm">
        <q-btn color="primary" icon="mdi-refresh" label="Refresh" @click="load" />
        <q-btn color="secondary" icon="mdi-play" label="Dry-run tick" @click="tick(false)" />
        <q-btn color="negative" outline icon="mdi-send" label="Execute tick" @click="tick(true)" />
      </div>
    </section>
    <q-card class="glass-card"><q-card-section>
      <div class="text-h6">Worker status</div>
      <pre class="code-block">{{ JSON.stringify(status, null, 2) }}</pre>
    </q-card-section></q-card>
    <q-card v-if="lastTick" class="glass-card"><q-card-section>
      <div class="text-h6">Last tick</div>
      <pre class="code-block">{{ JSON.stringify(lastTick, null, 2) }}</pre>
    </q-card-section></q-card>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { connectorsUrl, jsonFetch } from '../services/api'
const status = ref<any>({})
const lastTick = ref<any>(null)
async function load() { status.value = await jsonFetch(`${connectorsUrl}/api/connectors/worker/status`) }
async function tick(execute: boolean) {
  lastTick.value = await jsonFetch(`${connectorsUrl}/api/connectors/worker/tick`, { method: 'POST', body: JSON.stringify({ execute, limit: 25 }) })
  await load()
}
onMounted(load)
</script>
