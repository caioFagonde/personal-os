<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Knowledge" title="Zettelkasten" subtitle="Atomic notes, backlinks, tags, and Obsidian-compatible export.">
      <template #actions>
        <q-btn color="primary" icon="mdi-refresh" label="Refresh" :loading="loading" @click="load" />
      </template>
    </NexusPageHero>

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ error }}
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Create note</div>
        <div class="column q-gutter-md">
          <q-input v-model="draft.title" outlined label="Title" />
          <q-input v-model="draft.body" outlined label="Body" type="textarea" autogrow hint="Use [[Note Title]] to create backlinks." />
          <q-input v-model="tagText" outlined label="Tags, comma-separated" />
          <q-btn color="primary" unelevated label="Create note" icon="mdi-plus" :loading="creating" @click="createNote" />
        </div>
      </q-card-section>
    </q-card>

    <div v-if="loading && !notes.length" class="text-center q-py-xl">
      <q-spinner color="primary" size="40px" />
    </div>

    <div v-else-if="notes.length" class="module-grid">
      <q-card v-for="note in notes" :key="note.id" class="glass-card">
        <q-card-section>
          <div class="text-h6">{{ note.title }}</div>
          <div class="text-caption" style="color:var(--nexus-muted)">{{ note.note_type }} · {{ note.slug }}</div>
          <div class="row q-gutter-xs q-mt-xs">
            <q-chip v-for="tag in note.tags" :key="tag" dense outline size="sm">{{ tag }}</q-chip>
          </div>
          <p class="q-mt-sm ellipsis-3-lines" style="color:var(--nexus-muted);font-size:13px">{{ note.body }}</p>
        </q-card-section>
        <q-card-actions>
          <q-btn flat color="primary" size="sm" label="Open" @click="openNote(note.id)" />
          <q-btn flat color="primary" size="sm" label="Export" @click="exportNote(note.id)" />
        </q-card-actions>
      </q-card>
    </div>

    <NexusEmptyState v-else icon="mdi-graph-outline" message="No notes yet." hint="Create your first atomic note above." />

    <q-dialog v-model="dialog">
      <q-card class="glass-card" style="min-width: 60vw">
        <q-card-section>
          <pre class="code-block">{{ JSON.stringify(selected, null, 2) }}</pre>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Close" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import NexusEmptyState from '../components/NexusEmptyState.vue'
import { deviceKey, jsonFetch, moduleUrl } from '../services/api'

const notes = ref<any[]>([])
const error = ref('')
const loading = ref(false)
const creating = ref(false)
const selected = ref<any>({})
const dialog = ref(false)
const tagText = ref('')
const draft = ref({ title: '', body: '', note_type: 'permanent' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    notes.value = await jsonFetch<any[]>(`${moduleUrl}/api/zettelkasten/notes`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function createNote() {
  if (!draft.value.title.trim()) return
  creating.value = true
  error.value = ''
  try {
    await jsonFetch(`${moduleUrl}/api/zettelkasten/notes`, {
      method: 'POST',
      body: JSON.stringify({
        ...draft.value,
        device_key: deviceKey(),
        tags: tagText.value.split(',').map(s => s.trim()).filter(Boolean),
      }),
    })
    draft.value.title = ''
    draft.value.body = ''
    tagText.value = ''
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    creating.value = false
  }
}

async function openNote(id: string) {
  error.value = ''
  try {
    selected.value = await jsonFetch(`${moduleUrl}/api/zettelkasten/notes/${id}`)
    dialog.value = true
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function exportNote(id: string) {
  error.value = ''
  try {
    selected.value = await jsonFetch(`${moduleUrl}/api/zettelkasten/notes/${id}/obsidian`)
    dialog.value = true
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

onMounted(load)
</script>
