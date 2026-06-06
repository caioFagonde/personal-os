<template>
  <q-page class="q-pa-md column q-gutter-md">
    <section class="glass-panel q-pa-lg">
      <div class="text-h4">Study Companion</div>
      <p class="text-subtitle2 text-grey-4">Paste text, upload passages/photos, generate Zettelkasten notes, reading items, learning atoms, and retention reminders.</p>
      <q-tabs v-model="tab" dense align="left">
        <q-tab name="text" icon="mdi-text-box-plus-outline" label="Text" />
        <q-tab name="analog" icon="mdi-camera-iris" label="Analog" />
        <q-tab name="due" icon="mdi-brain" label="Due" />
      </q-tabs>
    </section>

    <section v-if="tab === 'text'" class="glass-panel q-pa-lg column q-gutter-md">
      <q-input v-model="title" filled label="Optional title" />
      <q-input v-model="studyText" type="textarea" autogrow filled label="Paste text" />
      <q-btn color="primary" icon="mdi-auto-fix" label="Store and learn" @click="ingestText" :loading="loading" />
    </section>

    <section v-if="tab === 'analog'" class="glass-panel q-pa-lg column q-gutter-md">
      <q-file v-model="file" filled label="Photo, screenshot, PDF, audio, or text file" />
      <q-input v-model="hint" type="textarea" autogrow filled label="Optional OCR/audio transcript hint" />
      <q-btn color="primary" icon="mdi-cloud-upload-outline" label="Process capture" @click="ingestAnalog" :disable="!file" :loading="loading" />
    </section>

    <section v-if="tab === 'due'" class="glass-panel q-pa-lg">
      <q-btn color="primary" icon="mdi-refresh" label="Load due reviews" @click="loadDue" />
      <q-list bordered separator class="q-mt-md">
        <q-item v-for="atom in due" :key="atom.id">
          <q-item-section>
            <q-item-label>{{ atom.concept }}</q-item-label>
            <q-item-label caption>stability {{ atom.stability }} · due {{ atom.due_at }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </section>

    <section v-if="result" class="glass-panel q-pa-lg">
      <div class="text-h6">Popup note</div>
      <p>{{ result.popup_note || result.title }}</p>
      <div class="row q-gutter-sm">
        <q-chip v-for="query in result.lookup_queries || []" :key="query" icon="mdi-magnify">{{ query }}</q-chip>
      </div>
      <pre class="result-json">{{ JSON.stringify(result, null, 2) }}</pre>
    </section>
  </q-page>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { jsonFetch, studyCompanionUrl, uploadFile } from '../services/api'
const tab = ref('text')
const title = ref('')
const studyText = ref('Spaced repetition improves retention by scheduling review just before forgetting. Desirable difficulty improves durable learning.')
const file = ref<File | null>(null)
const hint = ref('Principles of Learning\nChapter 1 page 7. Spaced repetition improves retention.')
const loading = ref(false)
const result = ref<any>(null)
const due = ref<any[]>([])
async function ingestText() {
  loading.value = true
  try { result.value = await jsonFetch(`${studyCompanionUrl}/api/study-companion/text`, { method: 'POST', body: JSON.stringify({ title: title.value || undefined, text: studyText.value }) }) }
  finally { loading.value = false }
}
async function ingestAnalog() {
  if (!file.value) return
  loading.value = true
  try {
    const form = new FormData()
    form.append('file', file.value)
    form.append('text_hint', hint.value)
    result.value = await uploadFile(`${studyCompanionUrl}/api/study-companion/analog`, form)
  } finally { loading.value = false }
}
async function loadDue() { due.value = await jsonFetch(`${studyCompanionUrl}/api/study-companion/due`) }
</script>
<style scoped>
.result-json { white-space: pre-wrap; opacity: .75; max-height: 360px; overflow: auto; }
</style>
