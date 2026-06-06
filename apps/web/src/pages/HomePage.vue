<template>
  <q-page class="home-page">
    <section class="hero glass-panel q-pa-xl">
      <div class="row items-center q-col-gutter-xl">
        <div class="col-12 col-lg-7">
          <div class="text-overline text-cyan-2">Phase 7 · Production cockpit</div>
          <h1 class="hero__title">One sovereign substrate. Every module, device, and workflow in formation.</h1>
          <p class="hero__subtitle">
            Local-first sync, authenticated service mesh, automation outbox, research ingestion, geospatial memory,
            and a mobile/desktop shell designed for daily use rather than demo-mode dashboards.
          </p>
          <div class="row q-gutter-sm q-mt-lg">
            <q-btn color="primary" unelevated rounded icon="mdi-refresh" label="Refresh substrate" @click="load" />
            <q-btn outline rounded color="cyan-2" icon="mdi-transit-connection-variant" label="Automation" to="/automation" />
            <q-btn outline rounded color="purple-2" icon="mdi-file-search-outline" label="Research" to="/research" />
          </div>
        </div>
        <div class="col-12 col-lg-5">
          <div class="mission-stack">
            <MetricCard label="Installed modules" :value="modules.length" icon="mdi-view-grid-plus-outline" />
            <MetricCard label="API state" :value="health.api?.status || 'unknown'" icon="mdi-server-network" />
            <MetricCard label="Automation" :value="health.automation?.status || 'unknown'" icon="mdi-robot-industrial-outline" />
          </div>
        </div>
      </div>
    </section>

    <section class="q-mt-lg">
      <div class="row q-col-gutter-md">
        <div class="col-6 col-md-3" v-for="card in healthCards" :key="card.label">
          <MetricCard :label="card.label" :value="card.value" :icon="card.icon" />
        </div>
      </div>
    </section>

    <section class="q-mt-xl">
      <div class="row items-end justify-between q-mb-md">
        <div>
          <div class="text-overline text-blue-grey-3">Specialized apps</div>
          <h2 class="q-my-none">Installed modules</h2>
        </div>
        <q-btn flat color="cyan-2" icon="mdi-sync" label="Rescan" @click="load" />
      </div>
      <div class="row q-col-gutter-md">
        <div class="col-12 col-md-6 col-xl-4" v-for="m in modules" :key="m.id">
          <q-card class="module-card glass-panel" flat>
            <q-card-section>
              <div class="row items-start no-wrap">
                <q-avatar class="module-card__avatar" rounded>{{ m.name?.slice(0, 1) }}</q-avatar>
                <div class="col q-ml-md">
                  <div class="text-h6">{{ m.name }}</div>
                  <div class="text-caption text-blue-grey-3">{{ m.id }} · v{{ m.version }} · {{ m.health }}</div>
                </div>
                <q-chip dense color="positive" text-color="dark" label="installed" />
              </div>
              <div class="q-mt-md module-card__chips">
                <q-chip dense outline v-for="p in (m.permissions || []).slice(0, 4)" :key="p">{{ p }}</q-chip>
              </div>
            </q-card-section>
            <q-card-actions align="right">
              <q-btn flat color="cyan-2" :to="m.routes?.web || `/modules/${m.id}`" label="Open module" icon-right="mdi-arrow-right" />
            </q-card-actions>
          </q-card>
        </div>
      </div>
    </section>
    <q-banner v-if="error" class="bg-negative text-white q-mt-md rounded-borders">{{ error }}</q-banner>
  </q-page>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import MetricCard from '../components/MetricCard.vue'
import { apiUrl, jsonFetch, syncUrl, moduleUrl, automationUrl } from '../services/api'
const modules = ref<any[]>([])
const health = ref<Record<string, any>>({})
const error = ref('')
const healthCards = computed(() => [
  { label: 'Modules', value: modules.value.length, icon: 'mdi-view-module-outline' },
  { label: 'API', value: health.value.api?.status || 'unknown', icon: 'mdi-api' },
  { label: 'Sync', value: health.value.sync?.status || 'unknown', icon: 'mdi-sync-circle' },
  { label: 'Module API', value: health.value.modules?.status || 'unknown', icon: 'mdi-puzzle-outline' },
  { label: 'Automation', value: health.value.automation?.status || 'unknown', icon: 'mdi-transit-connection-variant' }
])
async function safe<T>(promise: Promise<T>, fallback: T): Promise<T> {
  try { return await promise } catch { return fallback }
}
async function load() {
  error.value = ''
  try {
    const [apiHealth, syncHealth, moduleHealth, automationHealth, mods] = await Promise.all([
      safe(jsonFetch<any>(`${apiUrl}/health`), { status: 'offline' }),
      safe(jsonFetch<any>(`${syncUrl}/api/sync/health`), { status: 'offline' }),
      safe(jsonFetch<any>(`${moduleUrl}/health`), { status: 'offline' }),
      safe(jsonFetch<any>(`${automationUrl}/health`), { status: 'offline' }),
      jsonFetch<any[]>(`${apiUrl}/api/modules`)
    ])
    health.value = { api: apiHealth, sync: syncHealth, modules: moduleHealth, automation: automationHealth }
    modules.value = mods
  } catch (e: any) { error.value = e.message }
}
onMounted(load)
</script>
<style scoped>
.hero__title { font-size: clamp(38px, 7vw, 82px); line-height: .92; margin: 0; max-width: 980px; }
.hero__subtitle { color: var(--nexus-muted); font-size: clamp(16px, 2vw, 20px); max-width: 760px; }
.mission-stack { display: grid; gap: 14px; }
.module-card { min-height: 218px; }
.module-card__avatar { background: linear-gradient(135deg, var(--nexus-accent), var(--nexus-accent-2)); color: #06101a; font-weight: 900; }
.module-card__chips { min-height: 40px; }
</style>
