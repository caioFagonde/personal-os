<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Knowledge" title="Research" subtitle="Search lawful/open metadata sources, ingest authorized PDFs, extract chunks and citations, and search your local corpus.">
      <template #actions>
        <q-btn color="primary" icon="mdi-refresh" label="Refresh documents" :loading="loadingDocs" @click="loadDocuments" />
      </template>
    </NexusPageHero>

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ error }}
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <q-banner class="glass-card" rounded>
      <template #avatar><q-icon name="mdi-shield-check-outline" color="info" /></template>
      Source policy: open-access/public metadata, user uploads, and user-authorized URLs only.
    </q-banner>

    <div class="row q-col-gutter-md">
      <div class="col-12 col-lg-6">
        <q-card class="glass-card">
          <q-card-section>
            <div class="text-h6 q-mb-sm">Discovery search</div>
            <q-input v-model="query" outlined label="Query" />
            <q-select v-model="sources" outlined :options="sourceOptions" multiple use-chips label="Sources" class="q-mt-sm" />
          </q-card-section>
          <q-card-actions>
            <q-btn color="primary" unelevated label="Search" icon="mdi-magnify" :loading="searching" @click="runSearch" />
          </q-card-actions>
        </q-card>
      </div>
      <div class="col-12 col-lg-6">
        <q-card class="glass-card">
          <q-card-section>
            <div class="text-h6 q-mb-sm">Authorized PDF ingestion</div>
            <q-input v-model="pdfUrl" outlined label="Direct PDF URL" />
            <q-input v-model="uploadTitle" outlined label="Title override" class="q-mt-sm" />
            <q-file v-model="upload" outlined label="Upload local PDF" accept="application/pdf,.pdf" class="q-mt-sm">
              <template #prepend><q-icon name="mdi-paperclip" /></template>
            </q-file>
          </q-card-section>
          <q-card-actions>
            <q-btn color="primary" unelevated label="Fetch URL" :loading="fetching" @click="fetchPdf" />
            <q-btn color="secondary" unelevated label="Upload" :loading="uploading" @click="uploadPdf" />
          </q-card-actions>
        </q-card>
      </div>
    </div>

    <q-card v-if="results.length" class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Search results</div>
      </q-card-section>
      <q-list separator>
        <q-item v-for="r in results" :key="`${r.source}-${r.title}`">
          <q-item-section>
            <q-item-label>{{ r.title }}</q-item-label>
            <q-item-label caption>{{ r.source }} · {{ r.year || 'n.d.' }} · {{ (r.authors || []).slice(0, 3).join(', ') }}</q-item-label>
            <q-item-label caption class="q-mt-xs">{{ r.abstract }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-badge :color="r.is_open_access ? 'positive' : 'grey'">{{ r.is_open_access ? 'open' : 'metadata' }}</q-badge>
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Documents</div>
        <div class="row q-col-gutter-sm q-mb-md">
          <div class="col">
            <q-input v-model="localQuery" outlined label="Search local corpus" @keyup.enter="searchLocal" />
          </div>
          <div class="col-auto flex items-center">
            <q-btn color="primary" outline label="Search local" @click="searchLocal" />
          </div>
        </div>
      </q-card-section>
      <q-list v-if="documents.length" separator>
        <q-item v-for="d in documents" :key="d.id">
          <q-item-section>
            <q-item-label>{{ d.title }}</q-item-label>
            <q-item-label caption>{{ d.source_kind }} · {{ d.page_count || 0 }} pages · {{ d.text_status }} · {{ d.content_sha256?.slice(0, 12) }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
      <NexusEmptyState v-else icon="mdi-file-document-outline" message="No documents ingested yet." hint="Upload a PDF or fetch a URL above." />
    </q-card>

    <q-card v-if="localResults.length" class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Local matches</div>
      </q-card-section>
      <q-list separator>
        <q-item v-for="hit in localResults" :key="hit.chunk_id">
          <q-item-section>
            <q-item-label>{{ hit.title }}</q-item-label>
            <q-item-label caption v-html="hit.snippet" />
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import NexusEmptyState from '../components/NexusEmptyState.vue'
import { jsonFetch, researchUrl, uploadFile } from '../services/api'

const sourceOptions = ['arxiv', 'openalex', 'crossref', 'semantic_scholar']
const sources = ref(['arxiv', 'openalex', 'crossref'])
const query = ref('offline first sync conflict resolution')
const pdfUrl = ref('')
const uploadTitle = ref('')
const upload = ref<File | null>(null)
const results = ref<any[]>([])
const documents = ref<any[]>([])
const localQuery = ref('')
const localResults = ref<any[]>([])
const error = ref('')
const searching = ref(false)
const fetching = ref(false)
const uploading = ref(false)
const loadingDocs = ref(false)

async function runSearch() {
  error.value = ''
  searching.value = true
  try {
    const out = await jsonFetch<any>(`${researchUrl}/api/research/search`, {
      method: 'POST',
      body: JSON.stringify({ query: query.value, sources: sources.value, limit: 8 }),
    })
    results.value = out.results || []
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    searching.value = false
  }
}

async function fetchPdf() {
  error.value = ''
  fetching.value = true
  try {
    await jsonFetch<any>(`${researchUrl}/api/research/documents/fetch-url`, {
      method: 'POST',
      body: JSON.stringify({ url: pdfUrl.value, title: uploadTitle.value || undefined }),
    })
    await loadDocuments()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    fetching.value = false
  }
}

async function uploadPdf() {
  if (!upload.value) return
  error.value = ''
  uploading.value = true
  try {
    const form = new FormData()
    form.set('file', upload.value)
    if (uploadTitle.value) form.set('title', uploadTitle.value)
    await uploadFile<any>(`${researchUrl}/api/research/documents/upload`, form)
    upload.value = null
    await loadDocuments()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    uploading.value = false
  }
}

async function loadDocuments() {
  loadingDocs.value = true
  error.value = ''
  try {
    documents.value = await jsonFetch<any[]>(`${researchUrl}/api/research/documents`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loadingDocs.value = false
  }
}

async function searchLocal() {
  if (!localQuery.value.trim()) return
  error.value = ''
  try {
    localResults.value = await jsonFetch<any[]>(`${researchUrl}/api/research/local-search?q=${encodeURIComponent(localQuery.value)}`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

onMounted(loadDocuments)
</script>
