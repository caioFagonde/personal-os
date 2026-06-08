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

    <q-banner v-if="status?.demo_mode" class="bg-warning text-dark" rounded>
      <template #avatar><q-icon name="mdi-flask-outline" /></template>
      <strong>Demo mode</strong> — All runtimes are using heuristic fallbacks (keyword/regex matching). These are not suitable for production inference. Run <code>scripts/setup-models.sh</code> to install real providers.
    </q-banner>

    <q-banner v-else-if="status && status.production_ready" class="bg-positive text-white" rounded>
      <template #avatar><q-icon name="mdi-check-circle-outline" /></template>
      <strong>Production ready</strong> — All configured providers have been tested and certified.
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
              <div class="row items-center q-gutter-xs q-mt-xs">
                <q-badge :color="runtime.available ? 'positive' : 'warning'" :label="runtime.mode" />
                <q-badge v-if="runtime.demo" color="orange" text-color="dark" label="DEMO" />
                <q-badge v-else :color="stateColor(runtime.provider_state)" :label="runtime.provider_state" />
              </div>
              <div class="text-caption q-mt-sm" style="color:var(--nexus-muted)">{{ runtime.detail }}</div>
            </q-card-section>
          </q-card>
        </div>
      </div>
      <NexusEmptyState v-else icon="mdi-brain" message="No runtime info available." hint="Click 'Check runtimes' to load." />
    </q-card>

    <q-card v-if="providerList.length" class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Available providers</div>
        <div class="text-caption" style="color:var(--nexus-muted)">Install real providers to replace demo heuristics. Some require large model downloads — no downloads happen without explicit consent.</div>
      </q-card-section>
      <q-list separator>
        <q-item v-for="p in providerList" :key="p.name">
          <q-item-section>
            <q-item-label>{{ p.name }}</q-item-label>
            <q-item-label caption>{{ p.capability }} — {{ p.setup_hint }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <div class="row items-center q-gutter-xs">
              <q-badge v-if="p.requires_download" color="orange" text-color="dark" label="large download" />
              <q-badge :color="stateColor(p.state)" :label="p.state" />
            </div>
          </q-item-section>
        </q-item>
      </q-list>
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
const providerList = ref<any[]>([])
const error = ref('')
const loading = ref(false)

function stateColor(state: string): string {
  switch (state) {
    case 'tested': return 'positive'
    case 'configured': return 'info'
    case 'installed': return 'accent'
    default: return 'grey'
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [runtimeData, providerData] = await Promise.all([
      jsonFetch(`${modelRuntimeUrl}/api/model-runtime/runtimes`),
      jsonFetch(`${modelRuntimeUrl}/api/model-runtime/providers`),
    ])
    status.value = runtimeData
    providerList.value = providerData.providers || []
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
