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
        <q-btn flat                           icon="mdi-television-ambient-light"      label="Ambient mode"  to="/ambient" />
      </template>
    </NexusPageHero>

    <!-- Today strip: date + intention + inline capture prompt -->
    <q-card class="glass-card" data-testid="today-strip">
      <q-card-section class="row items-center q-col-gutter-md">
        <div class="col-12 col-md-4">
          <div class="text-caption" style="color:var(--nexus-muted)">{{ todayLine }}</div>
          <div class="text-subtitle1" v-if="dailyState?.opened">
            <q-icon name="mdi-target" size="16px" /> {{ dailyState.intention || 'No intention set' }}
            <q-badge v-if="dailyState.closed" color="primary" label="closed" class="q-ml-xs" />
          </div>
          <q-btn v-else flat dense color="primary" icon="mdi-weather-sunset-up" label="Open the day" to="/today" />
        </div>
        <div class="col-12 col-md-8">
          <q-input
            v-model="quickText"
            dense
            outlined
            placeholder="CAPTURE> type and hit Enter — /task, /note, /secretary…"
            @keyup.enter="quickCapture"
            :loading="capturing"
            data-testid="capture-prompt"
          >
            <template #prepend><q-icon name="mdi-chevron-right" /></template>
          </q-input>
        </div>
      </q-card-section>
    </q-card>

    <!-- Attention row: every chip is live and navigates to its source list -->
    <div class="row q-gutter-sm" v-if="attention.length" data-testid="attention-row">
      <q-chip
        v-for="chip in attention"
        :key="chip.label"
        clickable
        square
        :color="chip.tone === 'alarm' ? 'negative' : 'warning'"
        text-color="dark"
        :icon="chip.icon"
        @click="$router.push(chip.path)"
      >
        {{ chip.label }}
      </q-chip>
    </div>

    <!-- Status row -->
    <div class="row q-col-gutter-md">
      <div class="col-6 col-sm-3" v-for="metric in metrics" :key="metric.label">
        <MetricCard :label="metric.label" :value="metric.value" :icon="metric.icon" />
      </div>
    </div>

    <!-- Project radar + agent activity -->
    <div class="row q-col-gutter-md">
      <div class="col-12 col-lg-7">
        <q-card class="glass-card" data-testid="project-radar">
          <q-card-section>
            <div class="row items-center justify-between">
              <div class="text-h6">Project radar</div>
              <q-btn flat color="primary" size="sm" label="Projects" to="/projects" icon-right="mdi-arrow-right" />
            </div>
          </q-card-section>
          <q-separator dark />
          <q-list separator v-if="projectRadar.length">
            <q-item v-for="project in projectRadar" :key="project.id" clickable :to="`/projects?open=${project.id}`">
              <q-item-section avatar><q-icon name="mdi-folder-star-outline" /></q-item-section>
              <q-item-section>
                <q-item-label>{{ project.name }}</q-item-label>
                <q-item-label caption>{{ project.pitch || project.slug }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge outline color="primary" :label="`${project.linked ?? '…'} linked`" />
              </q-item-section>
            </q-item>
          </q-list>
          <q-card-section v-else>
            <div class="text-center q-py-sm" style="color:var(--nexus-muted)">No active projects. Create one on the Projects page.</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-lg-5">
        <q-card class="glass-card" data-testid="agent-feed">
          <q-card-section>
            <div class="row items-center justify-between">
              <div class="text-h6">Agent activity</div>
              <q-btn flat color="primary" size="sm" label="Agents" to="/coding-agent" icon-right="mdi-arrow-right" />
            </div>
          </q-card-section>
          <q-separator dark />
          <q-list separator v-if="agentJobs.length">
            <q-item v-for="job in agentJobs" :key="job.id">
              <q-item-section avatar>
                <q-icon
                  :name="job.status === 'failed' ? 'mdi-alert-circle-outline' : job.status === 'running' ? 'mdi-progress-clock' : 'mdi-robot-outline'"
                  :color="job.status === 'failed' ? 'negative' : job.status === 'pending_approval' ? 'warning' : 'primary'"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label lines="1">{{ job.title }}</q-item-label>
                <q-item-label caption>{{ job.status }} · {{ job.mode }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
          <q-card-section v-else>
            <div class="text-center q-py-sm" style="color:var(--nexus-muted)">No agent jobs yet.</div>
          </q-card-section>
        </q-card>
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
import { apiUrl, captureUrl, codingAgentUrl, connectorsUrl, jsonFetch, moduleUrl, syncUrl } from '../services/api'
import { graphNeighbors } from '../services/graph'
const modules = ref<any[]>([])
const apiHealth = ref<any>({ status: 'unknown' })
const connectorStatus = ref<Record<string, any>>({})
const agentStatus = ref<any>({})
const inboxCount = ref<number | undefined>(undefined)
const loading = ref(false)
const loadError = ref('')

// --- Today strip + inline capture prompt ------------------------------------
const dailyState = ref<{ opened: boolean; closed: boolean; intention?: string } | null>(null)
const quickText = ref('')
const capturing = ref(false)
const todayLine = new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })

async function quickCapture() {
  if (!quickText.value.trim()) return
  capturing.value = true
  try {
    await jsonFetch(`${captureUrl}/api/capture`, {
      method: 'POST',
      body: JSON.stringify({ text: quickText.value, source_kind: 'quick_capture' }),
    })
    quickText.value = ''
    pendingCaptures.value = (pendingCaptures.value ?? 0) + 1
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : String(err)
  } finally {
    capturing.value = false
  }
}

// --- Attention chips (all live; each navigates to its source list) -----------
const pendingCaptures = ref<number | undefined>(undefined)
const approvalsCount = ref(0)
const conflictsCount = ref(0)
const failedJobsCount = ref(0)
const backupHours = ref<number | null>(null)

interface AttentionChip { label: string; path: string; icon: string; tone: 'warn' | 'alarm' }

const attention = computed<AttentionChip[]>(() => {
  const chips: AttentionChip[] = []
  if (approvalsCount.value) chips.push({ label: `${approvalsCount.value} approval${approvalsCount.value > 1 ? 's' : ''} waiting`, path: '/coding-agent', icon: 'mdi-gavel', tone: 'warn' })
  if (conflictsCount.value) chips.push({ label: `${conflictsCount.value} sync conflict${conflictsCount.value > 1 ? 's' : ''}`, path: '/continuity?tab=conflicts', icon: 'mdi-source-branch', tone: 'alarm' })
  if (failedJobsCount.value) chips.push({ label: `${failedJobsCount.value} failed job${failedJobsCount.value > 1 ? 's' : ''}`, path: '/coding-agent', icon: 'mdi-alert-circle-outline', tone: 'alarm' })
  if (backupHours.value !== null && backupHours.value > 48) chips.push({ label: `backup ${Math.floor(backupHours.value / 24)}d old`, path: '/continuity?tab=backup', icon: 'mdi-cloud-alert', tone: 'warn' })
  return chips
})

// --- Project radar + agent feed ------------------------------------------------
const projectRadar = ref<{ id: string; name: string; slug: string; pitch: string; linked?: number }[]>([])
const agentJobs = ref<{ id: string; title: string; status: string; mode: string }[]>([])

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
    const [mods, health, connectors, agent, tasks, captures, daily, conflicts, jobs, outbox, manifests, projects] = await Promise.all([
      safe(jsonFetch<any[]>(`${apiUrl}/api/modules`), []),
      safe(jsonFetch<any>(`${apiUrl}/health`), { status: 'offline' }),
      safe(jsonFetch<Record<string, any>>(`${connectorsUrl}/api/connectors/status`), {}),
      safe(jsonFetch<any>(`${codingAgentUrl}/api/coding-agent/status`), {}),
      safe(jsonFetch<any[]>(`${captureUrl}/api/tasks?status=inbox`), null),
      safe(jsonFetch<any[]>(`${captureUrl}/api/capture/items?status=inbox`), null),
      safe(jsonFetch<any>(`${moduleUrl}/api/daily-state/today`), null),
      safe(jsonFetch<any[]>(`${syncUrl}/api/sync/conflicts`), []),
      safe(jsonFetch<any[]>(`${codingAgentUrl}/api/coding-agent/jobs`), []),
      safe(jsonFetch<any[]>(`${captureUrl}/api/outbox?status=pending_approval`), []),
      safe(jsonFetch<any[]>(`${connectorsUrl}/api/connectors/backup/manifests`), null),
      safe(jsonFetch<any[]>(`${moduleUrl}/api/projects?status=active`), []),
    ])
    modules.value = mods
    apiHealth.value = health
    connectorStatus.value = connectors
    agentStatus.value = agent
    if (tasks) inboxCount.value = tasks.length
    if (captures) pendingCaptures.value = captures.length
    dailyState.value = daily
    conflictsCount.value = conflicts.length
    agentJobs.value = jobs.slice(0, 5)
    approvalsCount.value = outbox.length + jobs.filter((j: any) => j.status === 'pending_approval').length
    failedJobsCount.value = jobs.filter((j: any) => j.status === 'failed').length
    if (manifests) {
      const latest = manifests[0]?.created_at
      backupHours.value = latest ? Math.floor((Date.now() - new Date(latest).getTime()) / 3_600_000) : null
    }
    projectRadar.value = projects.slice(0, 6)
    void enrichRadar()
    if (health.status === 'offline') loadError.value = 'API gateway unreachable'
  } catch (err) {
    loadError.value = String(err)
  } finally {
    loading.value = false
  }
}

// Linked-object counts come from the graph registry; enrichment is best-effort
// and the radar renders without it.
async function enrichRadar() {
  for (const project of projectRadar.value) {
    try {
      const detail = await jsonFetch<{ object_id?: string }>(`${moduleUrl}/api/projects/${project.id}`)
      if (detail.object_id) {
        const neighbors = await graphNeighbors(detail.object_id, 'belongs_to_project')
        project.linked = neighbors.length
      } else {
        project.linked = 0
      }
    } catch {
      project.linked = 0
    }
  }
}

onMounted(load)
</script>

