<template>
  <q-page class="column q-gutter-lg">

    <!-- Hero + quick actions -->
    <NexusPageHero eyebrow="Nexus Core" title="Command Center" subtitle="Sovereign personal operating substrate — capture, study, automate, and ship from one cockpit.">
      <template #actions>
        <q-btn unelevated color="primary"    icon="mdi-lightning-bolt-outline"         label="Capture"       to="/capture" />
        <q-btn unelevated color="secondary"  icon="mdi-checkbox-marked-circle-auto-outline" label="New task"  to="/tasks" />
        <q-btn outline                        icon="mdi-graph-outline"                  label="Add Zettel"    to="/zettelkasten" />
        <q-btn outline                        icon="mdi-camera-iris"                   label="Paste text"    to="/study-companion" />
        <q-btn outline                        icon="mdi-connection"                    label="Connectors"    to="/connectors" />
        <q-btn outline                        icon="mdi-code-braces"                   label="Coding job"    to="/coding-agent" />
      </template>
    </NexusPageHero>

    <!-- Status row -->
    <div class="row q-col-gutter-md">
      <div class="col-6 col-sm-3" v-for="metric in metrics" :key="metric.label">
        <MetricCard :label="metric.label" :value="metric.value" :icon="metric.icon" />
      </div>
    </div>

    <!-- Section: Today -->
    <div class="section-heading">Today</div>
    <div class="module-grid">
      <ModuleCard
        title="Capture"
        caption="Fast inbox"
        body="Quick notes, slash commands, task capture, and secretary delegation. The fastest path to getting things off your mind."
        path="/capture"
        icon="mdi-lightning-bolt-outline"
        group="today"
        :count="pendingCaptures"
        count-label="pending"
        primary-label="Open capture"
      />
      <ModuleCard
        title="Task Inbox"
        caption="Execution list"
        body="Review open tasks, delegated items, due dates, and follow-ups. Complete or delegate in one tap."
        path="/tasks"
        icon="mdi-checkbox-marked-circle-auto-outline"
        group="today"
        :count="inboxCount"
        count-label="inbox"
        primary-label="Open tasks"
      />
      <ModuleCard
        title="Digital Twin"
        caption="Personal state model"
        body="Goals, timeline, inferred state, recommendations, and privacy-aware memory policies."
        path="/digital-twin"
        icon="mdi-brain"
        group="today"
        primary-label="Open twin"
      />
    </div>

    <!-- Section: Knowledge -->
    <div class="section-heading">Knowledge</div>
    <div class="module-grid">
      <ModuleCard
        title="Study Companion"
        caption="Learning loop"
        body="Paste text, capture book passages or photos, generate learning atoms, and schedule spaced reviews."
        path="/study-companion"
        icon="mdi-camera-iris"
        group="knowledge"
        primary-label="Paste text"
        secondary-path="/study"
        secondary-label="Study notes"
      />
      <ModuleCard
        title="Zettelkasten"
        caption="Knowledge graph"
        body="Atomic notes, backlinks, tags, geospatial anchors, and Obsidian-compatible export."
        path="/zettelkasten"
        icon="mdi-graph-outline"
        group="knowledge"
        primary-label="Open notes"
      />
      <ModuleCard
        title="Research"
        caption="PDF & metadata"
        body="Open-access paper search, authorized PDF ingestion, chunking, citation extraction, and local full-text search."
        path="/research"
        icon="mdi-file-search-outline"
        group="knowledge"
        primary-label="Search papers"
      />
    </div>

    <!-- Section: Operations -->
    <div class="section-heading">Operations</div>
    <div class="module-grid">
      <ModuleCard
        title="Connectors"
        caption="OAuth · Messaging · Mesh"
        body="Onboard Google, Microsoft, Twilio, ntfy, and Tailscale. Manage encrypted refresh tokens and backup upload."
        path="/connectors"
        icon="mdi-connection"
        group="ops"
        :badge="connectorBadge"
        primary-label="Manage connectors"
      />
      <ModuleCard
        title="Sync Health"
        caption="Local-first continuity"
        body="Inspect sync log, device list, offline queue, and conflict resolution. Attachment checksums and push/pull health."
        path="/sync-health"
        icon="mdi-sync-circle"
        group="ops"
        primary-label="Check sync"
        secondary-path="/conflicts"
        secondary-label="Conflicts"
      />
      <ModuleCard
        title="Backup & Restore"
        caption="Continuity"
        body="Export config bundles, upload to Google Drive or OneDrive, and verify restore drill results."
        path="/backup-restore"
        icon="mdi-cloud-upload-outline"
        group="ops"
        primary-label="Open backup"
      />
    </div>

    <!-- Section: Development -->
    <div class="section-heading">Development</div>
    <div class="module-grid">
      <ModuleCard
        title="Coding Agent"
        caption="Claude Code remote jobs"
        body="Queue approval-gated coding tasks running on your home PC. Jobs are worktree-isolated, secret-scrubbed, and require explicit approval."
        path="/coding-agent"
        icon="mdi-code-braces"
        group="dev"
        :badge="agentBadge"
        primary-label="New job"
      />
      <ModuleCard
        title="Automation"
        caption="DAG workflows"
        body="Event-triggered DAG workflows, approval gates, n8n webhooks, interval schedulers, and bounded side-effect outbox."
        path="/automation"
        icon="mdi-transit-connection-variant"
        group="dev"
        primary-label="Open automation"
      />
    </div>

    <!-- Installed modules registry -->
    <q-card class="glass-card" v-if="modules.length">
      <q-card-section>
        <div class="row items-center justify-between">
          <div>
            <div class="text-h6">Installed modules</div>
            <div class="text-caption">Registry-backed modules discovered by the control plane.</div>
          </div>
          <q-btn flat color="primary" icon="mdi-sync" label="Rescan" :loading="loading" @click="load" />
        </div>
      </q-card-section>
      <q-card-section>
        <div class="row q-col-gutter-sm">
          <div class="col-12 col-sm-6 col-lg-4" v-for="m in modules" :key="m.id">
            <q-item class="glass-card" clickable :to="m.routes?.web || `/modules/${m.id}`" style="border-radius:16px">
              <q-item-section avatar>
                <q-avatar color="primary" text-color="dark" size="36px">{{ String(m.name || m.id).slice(0, 1).toUpperCase() }}</q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ m.name }}</q-item-label>
                <q-item-label caption>{{ m.id }} · v{{ m.version }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge :color="m.health === 'ok' ? 'positive' : 'warning'" :label="m.health || 'unknown'" />
              </q-item-section>
            </q-item>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <q-banner v-if="loadError" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ loadError }} — <strong>make up && make migrate</strong>
    </q-banner>

  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import MetricCard from '../components/MetricCard.vue'
import ModuleCard from '../components/NexusModuleCard.vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import { apiUrl, captureUrl, codingAgentUrl, connectorsUrl, jsonFetch } from '../services/api'
const modules = ref<any[]>([])
const apiHealth = ref<any>({ status: 'unknown' })
const connectorStatus = ref<Record<string, any>>({})
const agentStatus = ref<any>({})
const inboxCount = ref<number | undefined>(undefined)
const loading = ref(false)
const loadError = ref('')

const pendingCaptures = computed(() => undefined)

const metrics = computed(() => [
  { label: 'Modules',       value: modules.value.length || '—',   icon: 'mdi-view-module-outline' },
  { label: 'API',           value: apiHealth.value.status || '—', icon: 'mdi-api' },
  { label: 'Connectors',    value: configuredConnectors.value,     icon: 'mdi-connection' },
  { label: 'Tasks inbox',   value: inboxCount.value ?? '—',       icon: 'mdi-checkbox-marked-circle-auto-outline' },
])

const configuredConnectors = computed(() =>
  `${Object.values(connectorStatus.value).filter((x: any) => x?.configured).length}/${Object.keys(connectorStatus.value).length || 5}`
)

const connectorBadge = computed(() => {
  const total = Object.keys(connectorStatus.value).length
  if (!total) return undefined
  const ready = Object.values(connectorStatus.value).filter((x: any) => x?.configured).length
  return ready === total ? 'all ready' : `${ready}/${total}`
})

const agentBadge = computed(() => {
  if (!agentStatus.value.execute_enabled) return 'dry-run'
  return agentStatus.value.claude_available ? 'ready' : 'claude missing'
})

// ---------------------------------------------------------------------------
// Load
// ---------------------------------------------------------------------------
async function safe<T>(p: Promise<T>, fallback: T): Promise<T> {
  try { return await p } catch { return fallback }
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [mods, health, connectors, agent, tasks] = await Promise.all([
      safe(jsonFetch<any[]>(`${apiUrl}/api/modules`), []),
      safe(jsonFetch<any>(`${apiUrl}/health`), { status: 'offline' }),
      safe(jsonFetch<Record<string, any>>(`${connectorsUrl}/api/connectors/status`), {}),
      safe(jsonFetch<any>(`${codingAgentUrl}/api/coding-agent/status`), {}),
      safe(jsonFetch<any[]>(`${captureUrl}/api/tasks?status=inbox`), null),
    ])
    modules.value = mods
    apiHealth.value = health
    connectorStatus.value = connectors
    agentStatus.value = agent
    if (tasks) inboxCount.value = tasks.length
    if (health.status === 'offline') loadError.value = 'API gateway unreachable'
  } catch (err) {
    loadError.value = String(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

