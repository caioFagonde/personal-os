<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Operations" title="Connector Worker" subtitle="Drain WhatsApp, email, ntfy, automation, and backup delivery queues with auditable status." />

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ error }}
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <div class="row q-gutter-sm">
      <q-btn color="primary" icon="mdi-refresh" label="Refresh" :loading="loading" @click="load" />
      <q-btn color="secondary" icon="mdi-play" label="Dry-run tick" @click="tick(false)" />
      <q-btn color="negative" outline icon="mdi-send" label="Execute tick" @click="tick(true)" />
    </div>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6">Worker status</div>
        <q-list v-if="status && Object.keys(status).length" dense bordered separator class="rounded-borders q-mt-sm">
          <q-item v-for="(val, key) in status" :key="key">
            <q-item-section>{{ key }}</q-item-section>
            <q-item-section side class="text-weight-bold">{{ typeof val === 'object' ? JSON.stringify(val) : val }}</q-item-section>
          </q-item>
        </q-list>
        <div v-else class="text-caption q-mt-sm" style="color:var(--nexus-muted)">Click Refresh to load worker status.</div>
      </q-card-section>
    </q-card>

    <q-card v-if="lastTick" class="glass-card">
      <q-card-section>
        <div class="text-h6">Last tick result</div>
        <pre class="code-block">{{ JSON.stringify(lastTick, null, 2) }}</pre>
      </q-card-section>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import { connectorsUrl, jsonFetch } from '../services/api'

const status = ref<any>({})
const lastTick = ref<any>(null)
const error = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  try {
    status.value = await jsonFetch(`${connectorsUrl}/api/connectors/worker/status`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function tick(execute: boolean) {
  error.value = ''
  try {
    lastTick.value = await jsonFetch(`${connectorsUrl}/api/connectors/worker/tick`, {
      method: 'POST',
      body: JSON.stringify({ execute, limit: 25 }),
    })
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

onMounted(load)
</script>
