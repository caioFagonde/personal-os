<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Ops" title="Model Runtime" subtitle="Certified OCR, object detection, transcription, and multimodal capture bridge.">
      <template #actions>
        <q-btn color="primary" icon="mdi-heart-pulse" label="Check runtimes" :loading="loading" @click="load" />
        <q-btn outline icon="mdi-text-recognition" label="Process sample text" @click="processSample" />
      </template>
    </NexusPageHero>

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ error }}
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Runtime status</div>
      </q-card-section>
      <q-card-section v-if="loading && !status">
        <q-inner-loading showing color="primary" />
      </q-card-section>
      <div v-else-if="status?.runtimes?.length" class="row q-col-gutter-md q-pa-md">
        <div v-for="runtime in status.runtimes" :key="runtime.name" class="col-12 col-md-4">
          <q-card class="glass-card">
            <q-card-section>
              <div class="text-subtitle1 text-weight-bold">{{ runtime.name }}</div>
              <q-badge :color="runtime.available ? 'positive' : 'warning'" :label="runtime.mode" class="q-mt-xs" />
              <div class="text-caption q-mt-sm" style="color:var(--nexus-muted)">{{ runtime.detail }}</div>
            </q-card-section>
          </q-card>
        </div>
      </div>
      <NexusEmptyState v-else icon="mdi-brain" message="No runtime info available." hint="Click 'Check runtimes' to load." />
    </q-card>

    <q-card v-if="result" class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Sample result</div>
        <pre class="code-block">{{ JSON.stringify(result, null, 2) }}</pre>
      </q-card-section>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import NexusEmptyState from '../components/NexusEmptyState.vue'
import { jsonFetch, modelRuntimeUrl } from '../services/api'

const status = ref<any>(null)
const result = ref<any>(null)
const error = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  try {
    status.value = await jsonFetch(`${modelRuntimeUrl}/api/model-runtime/runtimes`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function processSample() {
  error.value = ''
  try {
    result.value = await jsonFetch(`${modelRuntimeUrl}/api/model-runtime/process-text`, {
      method: 'POST',
      body: JSON.stringify({ filename: 'sample.txt', text: 'A book passage about retrieval practice, spaced repetition, and diagrams.' }),
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

onMounted(load)
</script>
