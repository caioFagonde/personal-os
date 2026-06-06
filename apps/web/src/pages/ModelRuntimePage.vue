<template>
  <q-page class="q-pa-md q-gutter-md">
    <section class="hero-card glass-panel">
      <div class="text-overline">Phase 13</div>
      <h1>Model Runtime</h1>
      <p>Certified OCR, object detection, transcription, and multimodal capture bridge.</p>
      <div class="row q-gutter-sm">
        <q-btn color="primary" icon="mdi-heart-pulse" label="Check runtimes" @click="load" />
        <q-btn outline color="primary" icon="mdi-text-recognition" label="Process sample text" @click="processSample" />
      </div>
    </section>

    <q-card class="glass-panel">
      <q-card-section>
        <div class="text-h6">Runtime status</div>
        <q-banner v-if="error" class="bg-negative text-white q-mt-sm">{{ error }}</q-banner>
        <div class="row q-col-gutter-md q-mt-sm">
          <div v-for="runtime in status?.runtimes || []" :key="runtime.name" class="col-12 col-md-4">
            <q-card bordered flat>
              <q-card-section>
                <div class="text-subtitle1">{{ runtime.name }}</div>
                <q-chip :color="runtime.available ? 'positive' : 'warning'" text-color="white">{{ runtime.mode }}</q-chip>
                <div class="text-caption q-mt-sm">{{ runtime.detail }}</div>
              </q-card-section>
            </q-card>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <q-card class="glass-panel">
      <q-card-section>
        <div class="text-h6">Sample result</div>
        <pre class="result-box">{{ JSON.stringify(result, null, 2) }}</pre>
      </q-card-section>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { jsonFetch, modelRuntimeUrl } from '../services/api'

const status = ref<any>(null)
const result = ref<any>(null)
const error = ref('')

async function load() {
  error.value = ''
  try { status.value = await jsonFetch(`${modelRuntimeUrl}/api/model-runtime/runtimes`) }
  catch (err: any) { error.value = err.message }
}
async function processSample() {
  error.value = ''
  try {
    result.value = await jsonFetch(`${modelRuntimeUrl}/api/model-runtime/process-text`, {
      method: 'POST',
      body: JSON.stringify({ filename: 'sample.txt', text: 'A book passage about retrieval practice, spaced repetition, and diagrams.' })
    })
  } catch (err: any) { error.value = err.message }
}
onMounted(load)
</script>
<style scoped>
.result-box { white-space: pre-wrap; overflow: auto; max-height: 420px; }
</style>
