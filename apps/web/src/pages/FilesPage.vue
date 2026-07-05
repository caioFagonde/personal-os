<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero
      eyebrow="Core Daily"
      title="Files"
      subtitle="Artifacts stored on your PC — PDFs, images, and documents. Readable from any paired device over Tailscale."
    >
      <template #actions>
        <q-btn outline icon="mdi-refresh" label="Refresh" :loading="loading" @click="load" />
      </template>
    </NexusPageHero>

    <NexusErrorBanner v-if="error" :error="error" />

    <div v-if="loading && !files.length" class="text-center q-py-xl">
      <q-spinner color="primary" size="40px" />
    </div>

    <q-card v-else-if="files.length" class="glass-card">
      <q-list separator>
        <q-item v-for="f in files" :key="f.id" :data-testid="`file-${f.id}`">
          <q-item-section avatar>
            <q-icon :name="iconFor(f)" size="28px" color="primary" />
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ f.filename }}</q-item-label>
            <q-item-label caption>
              {{ f.content_type || 'unknown type' }} · {{ humanSize(f.size_bytes) }}
              <span v-if="f.module_id"> · {{ f.module_id }}</span>
              <q-badge v-if="f.encrypted" class="q-ml-sm" color="warning" text-color="dark" label="encrypted" />
            </q-item-label>
          </q-item-section>
          <q-item-section side>
            <div class="row q-gutter-xs">
              <q-btn flat dense color="primary" icon="mdi-eye-outline" :disable="f.encrypted" :loading="busyId === f.id" label="Open" @click="openFile(f)" />
              <q-btn flat dense icon="mdi-download-outline" :disable="f.encrypted" :loading="busyId === f.id" label="Save" @click="downloadFile(f)" />
            </div>
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <NexusEmptyState
      v-else
      icon="mdi-file-outline"
      message="No artifacts yet. Attach a PDF or file to a capture, task, or note and it will appear here."
    />

    <q-dialog v-model="viewer.open" @hide="closeViewer">
      <q-card class="glass-card" style="width:90vw;max-width:1000px;height:85vh">
        <q-bar>
          <q-icon :name="viewer.icon" />
          <div class="ellipsis">{{ viewer.name }}</div>
          <q-space />
          <q-btn dense flat icon="mdi-close" v-close-popup />
        </q-bar>
        <img v-if="viewer.kind === 'image'" :src="viewer.url" style="max-width:100%;max-height:100%;object-fit:contain;display:block;margin:auto" />
        <iframe v-else :src="viewer.url" style="width:100%;height:calc(85vh - 32px);border:0" />
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import NexusErrorBanner from '../components/NexusErrorBanner.vue'
import NexusEmptyState from '../components/NexusEmptyState.vue'
import { listAttachments, fetchAttachmentObjectUrl, type Attachment } from '../services/api'

const files = ref<Attachment[]>([])
const loading = ref(false)
const error = ref('')
const busyId = ref('')
const viewer = ref<{ open: boolean; url: string; name: string; kind: 'image' | 'other'; icon: string }>({
  open: false, url: '', name: '', kind: 'other', icon: 'mdi-file-outline',
})

function humanSize(bytes: number): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)))
  return `${(bytes / 1024 ** i).toFixed(i ? 1 : 0)} ${units[i]}`
}

function iconFor(f: Attachment): string {
  const t = f.content_type || ''
  if (t.startsWith('image/')) return 'mdi-file-image-outline'
  if (t === 'application/pdf') return 'mdi-file-pdf-box'
  if (t.startsWith('audio/')) return 'mdi-file-music-outline'
  if (t.startsWith('video/')) return 'mdi-file-video-outline'
  return 'mdi-file-document-outline'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    files.value = await listAttachments({ limit: 200 })
  } catch (e) {
    error.value = `Could not load files: ${(e as Error).message}`
  } finally {
    loading.value = false
  }
}

async function openFile(f: Attachment) {
  busyId.value = f.id
  try {
    const url = await fetchAttachmentObjectUrl(f.id)
    const isImage = (f.content_type || '').startsWith('image/')
    const isPdf = (f.content_type || '') === 'application/pdf'
    if (isImage || isPdf) {
      viewer.value = { open: true, url, name: f.filename, kind: isImage ? 'image' : 'other', icon: iconFor(f) }
    } else {
      // Non-previewable type: hand off to the browser/OS.
      window.open(url, '_blank')
    }
  } catch (e) {
    error.value = `Could not open ${f.filename}: ${(e as Error).message}`
  } finally {
    busyId.value = ''
  }
}

async function downloadFile(f: Attachment) {
  busyId.value = f.id
  try {
    const url = await fetchAttachmentObjectUrl(f.id)
    const a = document.createElement('a')
    a.href = url
    a.download = f.filename
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 30_000)
  } catch (e) {
    error.value = `Could not download ${f.filename}: ${(e as Error).message}`
  } finally {
    busyId.value = ''
  }
}

function closeViewer() {
  if (viewer.value.url) URL.revokeObjectURL(viewer.value.url)
  viewer.value = { open: false, url: '', name: '', kind: 'other', icon: 'mdi-file-outline' }
}

onMounted(load)
</script>
