<template>
  <q-page class="column q-gutter-lg">

    <section class="hero-panel">
      <div class="eyebrow">Core Daily</div>
      <h1>Fast Capture</h1>
      <p>Write once. The system creates a task, stores the note trail, and delegates when rules match.</p>
    </section>

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      <div>{{ errorMessage }}</div>
      <div v-if="errorAction" class="text-caption q-mt-xs" style="opacity:.85">{{ errorAction }}</div>
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Quick capture</div>
        <q-input
          v-model="text"
          type="textarea"
          outlined
          autogrow
          label="Capture command or note"
          :placeholder="placeholder"
          @keydown.ctrl.enter="capture"
          @keydown.meta.enter="capture"
        />
        <div class="text-caption q-mt-xs" style="color:var(--nexus-muted)">
          Ctrl+Enter to submit · Use /secretary to delegate
        </div>
      </q-card-section>
      <q-card-actions align="between">
        <div class="row q-gutter-xs">
          <q-btn outline size="sm" icon="mdi-account-tie" label="Secretary" @click="text = '/secretary whatsapp email due today 17h '" />
          <q-btn outline size="sm" icon="mdi-checkbox-marked-circle-auto-outline" label="Task" @click="text = '/task '" />
          <q-btn outline size="sm" icon="mdi-note-outline" label="Note" @click="text = '/note '" />
        </div>
        <q-btn color="primary" unelevated icon="mdi-lightning-bolt" label="Capture" :loading="loading" @click="capture" />
      </q-card-actions>
    </q-card>

    <q-card class="glass-card" v-if="result">
      <q-card-section>
        <div class="row items-center q-gutter-sm q-mb-md">
          <q-icon name="mdi-check-circle-outline" color="positive" size="24px" />
          <div class="text-h6">Captured</div>
        </div>
        <q-list dense bordered separator class="rounded-borders">
          <q-item>
            <q-item-section>Task</q-item-section>
            <q-item-section side class="text-weight-bold">{{ result.task?.title || '—' }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Status</q-item-section>
            <q-item-section side>
              <q-badge :label="result.task?.status || '—'" :color="result.task?.status === 'inbox' ? 'primary' : 'secondary'" />
            </q-item-section>
          </q-item>
          <q-item v-if="result.messages?.length">
            <q-item-section>Messages queued</q-item-section>
            <q-item-section side class="text-weight-bold">{{ result.messages.length }}</q-item-section>
          </q-item>
        </q-list>
        <q-list bordered separator class="q-mt-md" v-if="result.messages?.length">
          <q-item v-for="message in result.messages" :key="message.id">
            <q-item-section avatar>
              <q-icon :name="message.channel === 'whatsapp' ? 'mdi-whatsapp' : 'mdi-email-outline'" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ message.channel }} → {{ message.recipient }}</q-item-label>
              <q-item-label caption>{{ message.status }} · {{ message.connector }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
        <div class="row q-gutter-sm q-mt-md">
          <q-btn flat color="primary" label="Capture another" icon="mdi-lightning-bolt-outline" @click="reset" />
          <q-btn flat color="primary" label="View tasks" to="/tasks" icon-right="mdi-arrow-right" />
        </div>
      </q-card-section>
    </q-card>

  </q-page>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { captureUrl, jsonFetch } from '../services/api'

const placeholder = '/secretary whatsapp email due today 17h Ask João for the signed contract\n/task Finish report by Friday\n/note Idea: use a CRDT for notes'
const text = ref('')
const result = ref<any>(null)
const error = ref('')
const loading = ref(false)

const errorMessage = computed(() => {
  if (!error.value) return ''
  try {
    const idx = error.value.indexOf('{')
    if (idx >= 0) {
      const parsed = JSON.parse(error.value.slice(idx))
      const detail = parsed.detail || parsed.error
      if (detail && typeof detail === 'object') return detail.message || error.value
    }
  } catch { /* not JSON */ }
  return error.value
})

const errorAction = computed(() => {
  if (!error.value) return ''
  try {
    const idx = error.value.indexOf('{')
    if (idx >= 0) {
      const parsed = JSON.parse(error.value.slice(idx))
      const detail = parsed.detail || parsed.error
      if (detail && typeof detail === 'object') return detail.action || ''
    }
  } catch { /* not JSON */ }
  return ''
})

async function capture() {
  if (!text.value.trim()) return
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await jsonFetch<any>(`${captureUrl}/api/capture`, {
      method: 'POST',
      body: JSON.stringify({ text: text.value, source_kind: 'quick_capture' }),
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

function reset() {
  result.value = null
  text.value = ''
}
</script>
