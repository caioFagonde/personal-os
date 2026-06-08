<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Awareness" title="Intelligence Center" subtitle="Public OSINT monitoring — RSS, news, SearXNG keyword tracking, and daily briefings. Public sources only.">
      <template #actions>
        <q-btn color="primary" icon="mdi-refresh" label="Refresh" :loading="refreshing" @click="loadAll" />
      </template>
    </NexusPageHero>

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ error }}
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <q-banner class="glass-card" rounded>
      <template #avatar><q-icon name="mdi-shield-check-outline" color="info" /></template>
      Source policy: public RSS/Atom feeds, SearXNG queries, and user-configured public web sources only. No unauthorized surveillance, private-account access, or paywall bypassing.
    </q-banner>

    <!-- Sources + Monitors side-by-side -->
    <div class="row q-col-gutter-md">
      <!-- Sources -->
      <div class="col-12 col-lg-6">
        <q-card class="glass-card">
          <q-card-section>
            <div class="row items-center justify-between q-mb-sm">
              <div class="text-h6">Sources</div>
              <q-btn flat color="primary" icon="mdi-plus" size="sm" label="Add source" @click="showAddSource = true" />
            </div>
            <q-list separator v-if="sources.length">
              <q-item v-for="s in sources" :key="s.id">
                <q-item-section>
                  <q-item-label>{{ s.name }}</q-item-label>
                  <q-item-label caption>{{ s.kind }} {{ s.url ? '· ' + s.url : '' }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-badge :color="s.enabled ? 'positive' : 'grey'" :label="s.enabled ? 'active' : 'disabled'" />
                </q-item-section>
                <q-item-section side>
                  <q-btn flat round size="sm" icon="mdi-delete-outline" color="negative" @click="deleteSource(s.id)" />
                </q-item-section>
              </q-item>
            </q-list>
            <div v-else class="text-caption" style="color:var(--nexus-muted)">No sources configured yet.</div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Monitors -->
      <div class="col-12 col-lg-6">
        <q-card class="glass-card">
          <q-card-section>
            <div class="row items-center justify-between q-mb-sm">
              <div class="text-h6">Monitors</div>
              <q-btn flat color="primary" icon="mdi-plus" size="sm" label="Add monitor" @click="showAddMonitor = true" />
            </div>
            <q-list separator v-if="monitors.length">
              <q-item v-for="m in monitors" :key="m.id">
                <q-item-section>
                  <q-item-label>{{ m.name }}</q-item-label>
                  <q-item-label caption>{{ (m.keywords || []).join(', ') }} · {{ m.schedule }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-btn flat size="sm" color="primary" icon="mdi-play" label="Run" :loading="runningMonitor === m.id" @click="runMonitor(m.id)" />
                </q-item-section>
                <q-item-section side>
                  <q-btn flat round size="sm" icon="mdi-delete-outline" color="negative" @click="deleteMonitor(m.id)" />
                </q-item-section>
              </q-item>
            </q-list>
            <div v-else class="text-caption" style="color:var(--nexus-muted)">No monitors configured yet.</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- SearXNG search -->
    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Public search (SearXNG)</div>
        <div class="row q-col-gutter-sm">
          <div class="col">
            <q-input v-model="searchQuery" outlined label="Search public web / news" @keyup.enter="runSearch" />
          </div>
          <div class="col-auto flex items-center">
            <q-btn color="primary" unelevated label="Search" icon="mdi-magnify" :loading="searching" @click="runSearch" />
          </div>
        </div>
      </q-card-section>
      <q-list separator v-if="searchResults.length">
        <q-item v-for="(r, idx) in searchResults" :key="idx">
          <q-item-section>
            <q-item-label>{{ r.title }}</q-item-label>
            <q-item-label caption>{{ r.source }} · {{ r.published || 'n.d.' }}</q-item-label>
            <q-item-label caption class="q-mt-xs">{{ r.snippet }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-btn flat size="sm" icon="mdi-open-in-new" :href="r.url" target="_blank" v-if="r.url" />
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <!-- Findings -->
    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Recent findings</div>
      </q-card-section>
      <q-list separator v-if="findings.length">
        <q-item v-for="f in findings" :key="f.id">
          <q-item-section>
            <q-item-label>{{ f.title }}</q-item-label>
            <q-item-label caption>{{ f.snippet }}</q-item-label>
          </q-item-section>
          <q-item-section side top>
            <q-badge color="primary" :label="`${Math.round((f.relevance || 0) * 100)}%`" />
          </q-item-section>
          <q-item-section side>
            <q-btn flat size="sm" icon="mdi-open-in-new" :href="f.url" target="_blank" v-if="f.url" />
          </q-item-section>
        </q-item>
      </q-list>
      <q-card-section v-else>
        <div class="text-caption" style="color:var(--nexus-muted)">No findings yet. Add sources and run monitors to populate.</div>
      </q-card-section>
    </q-card>

    <!-- Briefings -->
    <q-card class="glass-card">
      <q-card-section>
        <div class="row items-center justify-between q-mb-sm">
          <div class="text-h6">Briefings</div>
          <q-btn flat color="primary" icon="mdi-file-document-plus-outline" label="Generate briefing" :loading="generatingBriefing" @click="generateBriefing" />
        </div>
      </q-card-section>
      <q-list separator v-if="briefings.length">
        <q-item v-for="b in briefings" :key="b.id">
          <q-item-section>
            <q-item-label>{{ b.title }}</q-item-label>
            <q-item-label caption>{{ b.finding_count }} findings · {{ b.status }} · {{ b.created_at }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-badge :color="b.status === 'complete' ? 'positive' : 'info'" :label="b.status" />
          </q-item-section>
        </q-item>
      </q-list>
      <q-card-section v-else>
        <div class="text-caption" style="color:var(--nexus-muted)">No briefings generated yet.</div>
      </q-card-section>
    </q-card>

    <!-- Add source dialog -->
    <q-dialog v-model="showAddSource">
      <q-card style="min-width:400px">
        <q-card-section>
          <div class="text-h6">Add public source</div>
        </q-card-section>
        <q-card-section>
          <q-input v-model="newSource.name" outlined label="Name" class="q-mb-sm" />
          <q-select v-model="newSource.kind" outlined :options="sourceKindOptions" label="Kind" class="q-mb-sm" />
          <q-input v-model="newSource.url" outlined label="URL (RSS/Atom feed or public endpoint)" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn unelevated color="primary" label="Add" :loading="addingSource" @click="addSource" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Add monitor dialog -->
    <q-dialog v-model="showAddMonitor">
      <q-card style="min-width:400px">
        <q-card-section>
          <div class="text-h6">Add keyword monitor</div>
        </q-card-section>
        <q-card-section>
          <q-input v-model="newMonitor.name" outlined label="Name" class="q-mb-sm" />
          <q-input v-model="keywordsInput" outlined label="Keywords (comma-separated)" class="q-mb-sm" />
          <q-select v-model="newMonitor.schedule" outlined :options="['hourly','daily','weekly']" label="Schedule" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn unelevated color="primary" label="Add" :loading="addingMonitor" @click="addMonitor" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import { intelligenceUrl, jsonFetch } from '../services/api'

const error = ref('')
const refreshing = ref(false)

const sources = ref<any[]>([])
const monitors = ref<any[]>([])
const findings = ref<any[]>([])
const briefings = ref<any[]>([])
const searchResults = ref<any[]>([])

const searchQuery = ref('')
const searching = ref(false)
const runningMonitor = ref<string | null>(null)
const generatingBriefing = ref(false)

const showAddSource = ref(false)
const addingSource = ref(false)
const newSource = ref({ name: '', kind: 'rss', url: '' })
const sourceKindOptions = ['rss', 'atom', 'searxng', 'news_api', 'public_web', 'user_configured']

const showAddMonitor = ref(false)
const addingMonitor = ref(false)
const newMonitor = ref({ name: '', schedule: 'daily' })
const keywordsInput = ref('')

async function safe<T>(p: Promise<T>, fallback: T): Promise<T> {
  try { return await p } catch { return fallback }
}

async function loadAll() {
  refreshing.value = true
  error.value = ''
  try {
    const [s, m, f, b] = await Promise.all([
      safe(jsonFetch<any[]>(`${intelligenceUrl}/api/intelligence/sources`), []),
      safe(jsonFetch<any[]>(`${intelligenceUrl}/api/intelligence/monitors`), []),
      safe(jsonFetch<any[]>(`${intelligenceUrl}/api/intelligence/findings`), []),
      safe(jsonFetch<any[]>(`${intelligenceUrl}/api/intelligence/briefings`), []),
    ])
    sources.value = s
    monitors.value = m
    findings.value = f
    briefings.value = b
  } catch (e: any) {
    error.value = e.message || 'Failed to load intelligence data'
  } finally {
    refreshing.value = false
  }
}

async function addSource() {
  addingSource.value = true
  try {
    await jsonFetch(`${intelligenceUrl}/api/intelligence/sources`, {
      method: 'POST',
      body: JSON.stringify(newSource.value),
    })
    showAddSource.value = false
    newSource.value = { name: '', kind: 'rss', url: '' }
    await loadAll()
  } catch (e: any) {
    error.value = e.message
  } finally {
    addingSource.value = false
  }
}

async function deleteSource(id: string) {
  try {
    await jsonFetch(`${intelligenceUrl}/api/intelligence/sources/${id}`, { method: 'DELETE' })
    await loadAll()
  } catch (e: any) {
    error.value = e.message
  }
}

async function addMonitor() {
  addingMonitor.value = true
  try {
    const keywords = keywordsInput.value.split(',').map(k => k.trim()).filter(Boolean)
    await jsonFetch(`${intelligenceUrl}/api/intelligence/monitors`, {
      method: 'POST',
      body: JSON.stringify({ ...newMonitor.value, keywords }),
    })
    showAddMonitor.value = false
    newMonitor.value = { name: '', schedule: 'daily' }
    keywordsInput.value = ''
    await loadAll()
  } catch (e: any) {
    error.value = e.message
  } finally {
    addingMonitor.value = false
  }
}

async function deleteMonitor(id: string) {
  try {
    await jsonFetch(`${intelligenceUrl}/api/intelligence/monitors/${id}`, { method: 'DELETE' })
    await loadAll()
  } catch (e: any) {
    error.value = e.message
  }
}

async function runMonitor(id: string) {
  runningMonitor.value = id
  try {
    await jsonFetch(`${intelligenceUrl}/api/intelligence/monitors/${id}/run`, { method: 'POST' })
    await loadAll()
  } catch (e: any) {
    error.value = e.message
  } finally {
    runningMonitor.value = null
  }
}

async function runSearch() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  try {
    const data = await jsonFetch<any>(`${intelligenceUrl}/api/intelligence/search`, {
      method: 'POST',
      body: JSON.stringify({ query: searchQuery.value }),
    })
    searchResults.value = data.results || []
  } catch (e: any) {
    error.value = e.message
  } finally {
    searching.value = false
  }
}

async function generateBriefing() {
  generatingBriefing.value = true
  try {
    await jsonFetch(`${intelligenceUrl}/api/intelligence/briefings/generate`, {
      method: 'POST',
      body: JSON.stringify({}),
    })
    await loadAll()
  } catch (e: any) {
    error.value = e.message
  } finally {
    generatingBriefing.value = false
  }
}

onMounted(loadAll)
</script>
