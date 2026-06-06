<template>
  <q-page padding>
    <div class="row items-center q-col-gutter-md">
      <div class="col-12 col-md-8">
        <h1>Research</h1>
        <p>Search lawful/open metadata sources, ingest authorized PDFs, extract chunks and citations, and search your local corpus.</p>
      </div>
      <div class="col-12 col-md-4 text-right">
        <q-btn color="primary" label="Refresh documents" @click="loadDocuments" />
      </div>
    </div>

    <q-banner class="bg-info text-white q-mb-md">
      Source policy: open-access/public metadata, user uploads, and user-authorized URLs only. Pirate-library and paywall-circumvention sources are blocked by the backend.
    </q-banner>

    <div class="row q-col-gutter-md">
      <div class="col-12 col-lg-6">
        <q-card bordered flat>
          <q-card-section>
            <div class="text-h6">Discovery search</div>
            <q-input v-model="query" label="Query" dense outlined />
            <q-select v-model="sources" :options="sourceOptions" multiple use-chips label="Sources" dense outlined class="q-mt-sm" />
          </q-card-section>
          <q-card-actions>
            <q-btn color="primary" label="Search" :loading="searching" @click="runSearch" />
          </q-card-actions>
        </q-card>
      </div>
      <div class="col-12 col-lg-6">
        <q-card bordered flat>
          <q-card-section>
            <div class="text-h6">Authorized PDF ingestion</div>
            <q-input v-model="pdfUrl" label="Direct PDF URL" dense outlined />
            <q-input v-model="uploadTitle" label="Title override" dense outlined class="q-mt-sm" />
            <q-file v-model="upload" label="Upload local PDF" accept="application/pdf,.pdf" dense outlined class="q-mt-sm" />
          </q-card-section>
          <q-card-actions>
            <q-btn color="primary" label="Fetch URL" :loading="fetching" @click="fetchPdf" />
            <q-btn color="secondary" label="Upload" :loading="uploading" @click="uploadPdf" />
          </q-card-actions>
        </q-card>
      </div>
    </div>

    <q-banner v-if="error" class="bg-negative text-white q-mt-md">{{ error }}</q-banner>

    <h2 class="q-mt-xl">Search results</h2>
    <q-list bordered separator v-if="results.length">
      <q-item v-for="r in results" :key="`${r.source}-${r.title}`">
        <q-item-section>
          <q-item-label>{{ r.title }}</q-item-label>
          <q-item-label caption>{{ r.source }} · {{ r.year || 'n.d.' }} · {{ (r.authors || []).slice(0, 3).join(', ') }}</q-item-label>
          <q-item-label caption>{{ r.abstract }}</q-item-label>
        </q-item-section>
        <q-item-section side>
          <q-badge :color="r.is_open_access ? 'positive' : 'grey'">{{ r.is_open_access ? 'open' : 'metadata' }}</q-badge>
        </q-item-section>
      </q-item>
    </q-list>

    <h2 class="q-mt-xl">Documents</h2>
    <q-input v-model="localQuery" label="Search local corpus" dense outlined class="q-mb-md" @keyup.enter="searchLocal" />
    <q-btn color="primary" outline label="Search local" @click="searchLocal" />
    <q-list bordered separator class="q-mt-md">
      <q-item v-for="d in documents" :key="d.id">
        <q-item-section>
          <q-item-label>{{ d.title }}</q-item-label>
          <q-item-label caption>{{ d.source_kind }} · {{ d.page_count || 0 }} pages · {{ d.text_status }} · {{ d.content_sha256?.slice(0, 12) }}</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>

    <h2 class="q-mt-xl" v-if="localResults.length">Local matches</h2>
    <q-list bordered separator v-if="localResults.length">
      <q-item v-for="hit in localResults" :key="hit.chunk_id">
        <q-item-section>
          <q-item-label>{{ hit.title }}</q-item-label>
          <q-item-label caption v-html="hit.snippet" />
        </q-item-section>
      </q-item>
    </q-list>
  </q-page>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
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

async function runSearch() {
  error.value = ''
  searching.value = true
  try {
    const out = await jsonFetch<any>(`${researchUrl}/api/research/search`, {
      method: 'POST',
      body: JSON.stringify({ query: query.value, sources: sources.value, limit: 8 })
    })
    results.value = out.results || []
  } catch (e: any) { error.value = e.message } finally { searching.value = false }
}

async function fetchPdf() {
  error.value = ''
  fetching.value = true
  try {
    await jsonFetch<any>(`${researchUrl}/api/research/documents/fetch-url`, {
      method: 'POST',
      body: JSON.stringify({ url: pdfUrl.value, title: uploadTitle.value || undefined })
    })
    await loadDocuments()
  } catch (e: any) { error.value = e.message } finally { fetching.value = false }
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
  } catch (e: any) { error.value = e.message } finally { uploading.value = false }
}

async function loadDocuments() {
  try { documents.value = await jsonFetch<any[]>(`${researchUrl}/api/research/documents`) } catch (e: any) { error.value = e.message }
}

async function searchLocal() {
  if (!localQuery.value.trim()) return
  try { localResults.value = await jsonFetch<any[]>(`${researchUrl}/api/research/local-search?q=${encodeURIComponent(localQuery.value)}`) } catch (e: any) { error.value = e.message }
}

onMounted(loadDocuments)
</script>
