<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Operations" title="Sync Health" subtitle="Control-plane health, connector readiness, sync conflicts, and continuity status.">
      <template #actions>
        <q-btn color="primary" icon="mdi-heart-pulse" label="Run health check" :loading="loading" @click="load" />
      </template>
    </NexusPageHero>

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ error }}
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <q-card v-if="health" class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Service Health</div>
        <q-list dense bordered separator class="rounded-borders">
          <q-item v-for="(val, key) in health.services || {}" :key="key">
            <q-item-section>{{ key }}</q-item-section>
            <q-item-section side>
              <q-badge :color="val?.ok ? 'positive' : 'negative'" :label="val?.ok ? 'OK' : 'Down'" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>

    <q-card v-if="connectors && Object.keys(connectors).length" class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Connector Status</div>
        <q-list dense bordered separator class="rounded-borders">
          <q-item v-for="(val, key) in connectors" :key="key">
            <q-item-section>{{ key }}</q-item-section>
            <q-item-section side>
              <q-badge :color="val?.configured ? 'positive' : 'grey'" :label="val?.configured ? 'Configured' : 'Not configured'" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import { apiUrl, connectorsUrl, jsonFetch } from '../services/api'

const health = ref<any>(null)
const connectors = ref<any>(null)
const error = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [h, c] = await Promise.all([
      jsonFetch(`${apiUrl}/api/control/health`),
      jsonFetch(`${connectorsUrl}/api/connectors/status`),
    ])
    health.value = h
    connectors.value = c
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}
</script>
