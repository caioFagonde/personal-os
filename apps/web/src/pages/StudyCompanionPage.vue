<template>
  <q-page class="column q-gutter-lg">

    <section class="hero-panel">
      <div class="eyebrow">Growth</div>
      <h1>Study Companion</h1>
      <p>Paste text, upload passages or photos, generate learning atoms, and schedule spaced repetition reviews.</p>
    </section>

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ error }}
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <q-card class="glass-card">
      <q-tabs v-model="tab" dense align="left" no-caps active-color="primary" indicator-color="primary">
        <q-tab name="text"   icon="mdi-text-box-plus-outline" label="Paste text" />
        <q-tab name="analog" icon="mdi-camera-iris"          label="Analog capture" />
        <q-tab name="due"    icon="mdi-brain"                 label="Due reviews" />
      </q-tabs>
      <q-separator dark />

      <!-- Text capture tab -->
      <q-card-section v-if="tab === 'text'" class="column q-gutter-md">
        <q-input v-model="title" outlined label="Optional title (leave blank to infer)" clearable />
        <q-input
          v-model="studyText"
          type="textarea"
          outlined
          autogrow
          label="Paste text, passage, or learning material"
          hint="The system will create a Zettelkasten note, extract learning atoms, and schedule reviews."
        />
        <q-btn
          color="primary"
          unelevated
          icon="mdi-auto-fix"
          label="Store and generate learning atoms"
          :loading="loading"
          :disable="!studyText.trim()"
          @click="ingestText"
        />
      </q-card-section>

      <!-- Analog capture tab -->
      <q-card-section v-if="tab === 'analog'" class="column q-gutter-md">
        <q-file v-model="file" outlined label="Photo, screenshot, PDF, audio, or text file" accept="image/*,audio/*,.pdf,.txt,.md">
          <template #prepend><q-icon name="mdi-paperclip" /></template>
        </q-file>
        <q-input
          v-model="hint"
          type="textarea"
          outlined
          autogrow
          label="OCR/transcript hint (optional)"
          placeholder="Chapter, author, or page context to improve extraction accuracy"
        />
        <q-btn
          color="primary"
          unelevated
          icon="mdi-cloud-upload-outline"
          label="Process capture"
          :loading="loading"
          :disable="!file"
          @click="ingestAnalog"
        />
      </q-card-section>

      <!-- Due reviews tab -->
      <q-card-section v-if="tab === 'due'">
        <q-btn outline icon="mdi-refresh" label="Load due reviews" :loading="loading" @click="loadDue" class="q-mb-md" />
        <div v-if="!due.length && !loading" class="text-muted text-center q-py-lg">
          <q-icon name="mdi-check-all" size="48px" style="opacity:.3" /><br>
          No reviews due right now.
        </div>
        <q-list bordered separator class="rounded-borders" v-if="due.length">
          <q-item v-for="atom in due" :key="atom.id" class="q-py-md">
            <q-item-section>
              <q-item-label class="text-weight-bold">{{ atom.concept }}</q-item-label>
              <q-item-label caption>stability {{ atom.stability?.toFixed(2) }} · due {{ formatDate(atom.due_at) }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-badge color="primary" label="review" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>

    <!-- Result panel — structured, not raw JSON -->
    <q-card class="glass-card" v-if="result">
      <q-card-section>
        <div class="row items-center q-gutter-sm q-mb-md">
          <q-icon name="mdi-check-circle-outline" color="positive" size="24px" />
          <div class="text-h6">Processed</div>
        </div>

        <div v-if="result.popup_note || result.title" class="q-mb-md">
          <div class="text-caption text-muted q-mb-xs">Note title</div>
          <div class="text-body1 text-weight-bold">{{ result.popup_note || result.title }}</div>
        </div>

        <div v-if="result.slug" class="q-mb-md">
          <div class="text-caption text-muted q-mb-xs">Slug</div>
          <code class="text-accent">{{ result.slug }}</code>
        </div>

        <div v-if="result.atoms?.length" class="q-mb-md">
          <div class="text-caption text-muted q-mb-xs">Learning atoms ({{ result.atoms.length }})</div>
          <q-list dense bordered separator class="rounded-borders">
            <q-item v-for="atom in result.atoms" :key="atom.id ?? atom.concept">
              <q-item-section>
                <q-item-label>{{ atom.concept }}</q-item-label>
                <q-item-label caption>{{ atom.details }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </div>

        <div v-if="result.lookup_queries?.length" class="q-mb-md">
          <div class="text-caption text-muted q-mb-xs">Research queries</div>
          <div class="row q-gutter-xs">
            <q-chip v-for="query in result.lookup_queries" :key="query" icon="mdi-magnify" size="sm">{{ query }}</q-chip>
          </div>
        </div>

        <div v-if="result.ocr_text || result.transcript" class="q-mb-md">
          <div class="text-caption text-muted q-mb-xs">Extracted text</div>
          <pre class="code-block">{{ result.ocr_text || result.transcript }}</pre>
        </div>
      </q-card-section>
      <q-card-actions>
        <q-btn flat color="primary" label="Capture another" @click="result = null" />
        <q-btn flat color="primary" label="View due reviews" @click="tab = 'due'; loadDue()" />
      </q-card-actions>
    </q-card>

  </q-page>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { jsonFetch, studyCompanionUrl, uploadFile } from '../services/api'

const tab = ref('text')
const title = ref('')
const studyText = ref('')
const file = ref<File | null>(null)
const hint = ref('')
const loading = ref(false)
const error = ref('')
const result = ref<any>(null)
const due = ref<any[]>([])

function formatDate(iso: string): string {
  try { return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) } catch { return iso }
}

async function ingestText() {
  if (!studyText.value.trim()) return
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await jsonFetch<any>(`${studyCompanionUrl}/api/study-companion/text`, {
      method: 'POST',
      body: JSON.stringify({ title: title.value || undefined, text: studyText.value }),
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function ingestAnalog() {
  if (!file.value) return
  loading.value = true
  error.value = ''
  result.value = null
  try {
    const form = new FormData()
    form.append('file', file.value)
    form.append('text_hint', hint.value)
    result.value = await uploadFile<any>(`${studyCompanionUrl}/api/study-companion/analog`, form)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function loadDue() {
  loading.value = true
  error.value = ''
  try {
    due.value = await jsonFetch<any[]>(`${studyCompanionUrl}/api/study-companion/due`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}
</script>
