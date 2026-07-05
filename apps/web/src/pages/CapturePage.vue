<template>
  <q-page class="column q-gutter-lg">

    <NexusPageHero eyebrow="Core Daily" title="Fast Capture" subtitle="Write once. The system creates a task, stores the note trail, and delegates when rules match." />

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

    <!-- Triage inbox (Phase C4): keyboard-first — j/k move, t task, n note, a archive -->
    <q-card class="glass-card">
      <q-card-section>
        <div class="row items-center justify-between">
          <div class="text-h6">Inbox triage</div>
          <div class="text-caption" style="color:var(--nexus-muted)">j/k move · t open task · n → note · a archive</div>
        </div>
      </q-card-section>
      <q-separator dark />
      <q-list separator v-if="items.length" data-testid="capture-inbox">
        <q-item
          v-for="(item, index) in items"
          :key="item.id"
          clickable
          :active="index === selected"
          active-class="triage-row--active"
          @click="selected = index"
        >
          <q-item-section avatar>
            <q-icon :name="item.task_id ? 'mdi-checkbox-marked-circle-outline' : 'mdi-tray-arrow-down'" size="20px" />
          </q-item-section>
          <q-item-section>
            <q-item-label lines="2">{{ item.raw_text }}</q-item-label>
            <q-item-label caption>{{ item.source_kind }} · {{ formatWhen(item.created_at) }}<span v-if="item.task_title"> · task: {{ item.task_title }}</span></q-item-label>
          </q-item-section>
          <q-item-section side>
            <div class="row q-gutter-xs">
              <q-btn v-if="item.task_id" flat round size="sm" icon="mdi-checkbox-marked-circle-outline" color="primary" title="Open task (t)" to="/tasks" />
              <q-btn flat round size="sm" icon="mdi-note-plus-outline" color="primary" title="Promote to note (n)" @click.stop="promoteToNote(item)" />
              <q-btn flat round size="sm" icon="mdi-archive-arrow-down-outline" color="grey" title="Archive (a)" @click.stop="archive(item)" />
            </div>
          </q-item-section>
        </q-item>
      </q-list>
      <q-card-section v-else>
        <div class="text-center q-py-md" style="color:var(--nexus-muted)">
          No captures in the inbox. Press C to capture.
        </div>
      </q-card-section>
    </q-card>

  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { captureUrl, deviceKey, jsonFetch, moduleUrl } from '../services/api'

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
    await loadInbox()
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

// --- Inbox triage (Phase C4) -------------------------------------------------
interface CaptureItem {
  id: string
  raw_text: string
  source_kind: string
  status: string
  created_at: string
  task_id: string | null
  task_title: string | null
}

const router = useRouter()
const items = ref<CaptureItem[]>([])
const selected = ref(0)

function formatWhen(iso: string): string {
  try { return new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) } catch { return iso }
}

async function loadInbox() {
  try {
    items.value = await jsonFetch<CaptureItem[]>(`${captureUrl}/api/capture/items?status=inbox`)
    selected.value = Math.min(selected.value, Math.max(0, items.value.length - 1))
  } catch {
    items.value = [] // the empty state stands in; the capture form still works
  }
}

async function archive(item: CaptureItem) {
  try {
    await jsonFetch(`${captureUrl}/api/capture/items/${item.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: 'archived' }),
    })
    await loadInbox()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function promoteToNote(item: CaptureItem) {
  try {
    const firstLine = item.raw_text.trim().split('\n')[0].slice(0, 120) || 'Captured note'
    const note = await jsonFetch<{ id: string }>(`${moduleUrl}/api/zettelkasten/notes`, {
      method: 'POST',
      body: JSON.stringify({ title: firstLine, body: item.raw_text, note_type: 'fleeting', device_key: deviceKey(), tags: ['capture'] }),
    })
    await jsonFetch(`${captureUrl}/api/capture/items/${item.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: 'triaged', triaged_note_id: note.id }),
    })
    await loadInbox()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

function onTriageKeydown(event: KeyboardEvent) {
  // Never steal keys from the capture textarea / inputs.
  const target = event.target as HTMLElement | null
  if (target && ['INPUT', 'TEXTAREA'].includes(target.tagName)) return
  const item = items.value[selected.value]
  switch (event.key) {
    case 'j': selected.value = Math.min(selected.value + 1, items.value.length - 1); break
    case 'k': selected.value = Math.max(selected.value - 1, 0); break
    case 't': if (item?.task_id) void router.push('/tasks'); break
    case 'n': if (item) void promoteToNote(item); break
    case 'a': if (item) void archive(item); break
  }
}

const route = useRoute()

onMounted(() => {
  // Android/desktop share-target opens Capture pre-filled (Phase E2).
  if (typeof route.query.text === 'string') text.value = route.query.text
  void loadInbox()
  window.addEventListener('keydown', onTriageKeydown)
})
onUnmounted(() => window.removeEventListener('keydown', onTriageKeydown))
</script>
<style scoped lang="scss">
.triage-row--active {
  background: var(--nexus-text, #5dff86);
  color: var(--nexus-ink, #07130b);
  text-shadow: none;
}
</style>
