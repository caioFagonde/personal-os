<template>
  <q-page class="column q-gutter-lg">
    <section class="hero-panel">
      <div class="eyebrow">Phase 14 · Claude Code</div>
      <h1>Coding Agent</h1>
      <p>Queue approval-gated coding work on your home PC. Jobs run in isolated git worktrees, scrub secrets from the environment, capture logs and artifacts, and require approval before execution.</p>
      <div class="row q-gutter-sm q-mt-md">
        <q-btn color="primary" icon="mdi-refresh" label="Refresh" :loading="loading" @click="load" />
        <q-btn outline :icon="status.execute_enabled ? 'mdi-play-circle-outline' : 'mdi-shield-check-outline'" :label="status.execute_enabled ? 'Execution enabled' : 'Dry-run mode'" :color="status.execute_enabled ? 'warning' : 'primary'" />
      </div>
    </section>

    <q-banner v-if="loadError" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ loadError }}
    </q-banner>

    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-4">
        <q-card class="glass-card full-height">
          <q-card-section>
            <div class="text-h6 q-mb-sm">Runtime</div>
            <q-list dense>
              <q-item>
                <q-item-section>Claude command</q-item-section>
                <q-item-section side class="text-muted">{{ status.claude_command || 'claude' }}</q-item-section>
              </q-item>
              <q-item>
                <q-item-section>Claude available</q-item-section>
                <q-item-section side>
                  <q-badge :color="status.claude_available ? 'positive' : 'warning'" :label="status.claude_available ? 'yes' : 'not found'" />
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section>Git available</q-item-section>
                <q-item-section side>
                  <q-badge :color="status.git_available ? 'positive' : 'negative'" :label="status.git_available ? 'yes' : 'no'" />
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section>Execution mode</q-item-section>
                <q-item-section side>
                  <q-badge :color="status.execute_enabled ? 'warning' : 'info'" :label="status.execute_enabled ? 'enabled' : 'dry-run'" />
                </q-item-section>
              </q-item>
              <q-item v-if="status.allowed_repo_roots?.length">
                <q-item-section>Allowed roots</q-item-section>
                <q-item-section side class="text-muted" style="font-size:11px;max-width:160px;text-align:right;word-break:break-all">
                  {{ status.allowed_repo_roots.join(', ') }}
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-md-8">
        <q-card class="glass-card">
          <q-card-section>
            <div class="text-h6">New remote coding job</div>
            <p class="text-muted">Example: "Add a dashboard card showing failed connector deliveries. Include tests. Do not touch secrets."</p>
            <div class="row q-col-gutter-md q-mt-xs">
              <div class="col-12 col-md-8">
                <q-input v-model="form.title" outlined label="Title" :rules="[v => v.length >= 3 || 'At least 3 characters']" />
              </div>
              <div class="col-12 col-md-4">
                <q-select v-model="form.mode" outlined :options="modes" label="Mode" />
              </div>
              <div class="col-12">
                <q-input v-model="form.prompt" outlined type="textarea" autogrow label="Prompt" :rules="[v => v.length >= 8 || 'At least 8 characters']" />
              </div>
              <div class="col-12 col-md-8">
                <q-input v-model="form.repo_path" outlined label="Repo path" hint="Leave blank to use server default." />
              </div>
              <div class="col-12 col-md-4 flex items-center">
                <q-toggle v-model="form.auto_approve" label="Auto-approve (skip manual step)" color="warning" />
              </div>
            </div>
          </q-card-section>
          <q-card-actions align="right">
            <q-btn color="primary" icon="mdi-send" label="Create job" :loading="creating" @click="createJob" />
          </q-card-actions>
        </q-card>
      </div>
    </div>

    <q-card class="glass-card">
      <q-card-section>
        <div class="row items-center justify-between">
          <div>
            <div class="text-h6">Jobs <q-badge v-if="jobs.length" :label="jobs.length" color="primary" class="q-ml-xs" /></div>
            <div class="text-caption">Approve, dry-run, or execute Claude Code worktree jobs. Execution requires the job to be in <code>queued</code> status.</div>
          </div>
          <q-btn flat color="primary" icon="mdi-refresh" label="Refresh" :loading="loading" @click="load" />
        </div>
      </q-card-section>
      <q-separator dark />
      <q-card-section v-if="!jobs.length && !loading">
        <div class="text-muted text-center q-py-lg">No jobs yet. Create one above.</div>
      </q-card-section>
      <q-card-section v-else>
        <q-list bordered separator class="rounded-borders">
          <q-item v-for="job in jobs" :key="job.id" class="q-py-md">
            <q-item-section>
              <q-item-label class="text-weight-bold">{{ job.title }}</q-item-label>
              <q-item-label caption>
                <q-badge :color="statusColor(job.status)" :label="job.status" class="q-mr-xs" />
                {{ job.mode }} · {{ job.branch_name }}
              </q-item-label>
              <q-item-label caption class="text-muted">{{ job.repo_path }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="row q-gutter-xs">
                <q-btn
                  v-if="job.status === 'pending_approval'"
                  size="sm"
                  color="positive"
                  icon="mdi-check"
                  label="Approve"
                  @click="approve(job.id)"
                />
                <q-btn
                  v-if="job.status === 'queued' || job.status === 'completed' || job.status === 'failed'"
                  size="sm"
                  outline
                  color="primary"
                  icon="mdi-eye-outline"
                  label="Dry run"
                  @click="run(job.id, false)"
                />
                <q-btn
                  v-if="job.status === 'queued' || job.status === 'completed' || job.status === 'failed'"
                  size="sm"
                  :color="status.execute_enabled ? 'warning' : 'grey'"
                  icon="mdi-play"
                  label="Execute"
                  @click="confirmRun(job.id)"
                />
              </div>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>

    <q-card class="glass-card" v-if="runResult">
      <q-card-section>
        <div class="row items-center justify-between q-mb-sm">
          <div class="text-h6">Latest run result</div>
          <q-badge :color="statusColor(runResult.status)" :label="runResult.status" />
        </div>
        <div v-if="runResult.worktree_path" class="text-caption text-muted q-mb-sm">
          Worktree: <code>{{ runResult.worktree_path }}</code>
        </div>
      </q-card-section>
      <q-card-section v-if="runResult.stdout">
        <div class="text-caption text-muted q-mb-xs">stdout</div>
        <pre class="code-block">{{ runResult.stdout }}</pre>
      </q-card-section>
      <q-card-section v-if="runResult.stderr">
        <div class="text-caption text-muted q-mb-xs">stderr</div>
        <pre class="code-block" style="border-color:rgba(251,113,133,0.3)">{{ runResult.stderr }}</pre>
      </q-card-section>
      <q-card-section v-if="runResult.artifacts?.length">
        <div class="text-caption text-muted q-mb-xs">artifacts</div>
        <div v-for="(a, i) in runResult.artifacts" :key="i" class="q-mb-sm">
          <q-badge :label="a.kind" color="primary" class="q-mr-xs" />
          <pre class="code-block q-mt-xs" v-if="a.content">{{ a.content }}</pre>
        </div>
      </q-card-section>
    </q-card>

    <q-card class="glass-card" v-if="actionError">
      <q-card-section>
        <div class="text-h6 text-negative q-mb-xs"><q-icon name="mdi-alert-circle-outline" class="q-mr-xs" />Error</div>
        <pre class="code-block">{{ actionError }}</pre>
      </q-card-section>
    </q-card>

    <q-dialog v-model="confirmDialog">
      <q-card class="glass-card" style="min-width:340px">
        <q-card-section>
          <div class="text-h6">Confirm execution</div>
          <p class="q-mt-sm">This will run Claude Code in a git worktree{{ status.execute_enabled ? '' : ' (dry-run — CODING_AGENT_EXECUTE is false)' }}. Execution is irreversible until you review and discard the worktree manually.</p>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn color="warning" label="Run" icon="mdi-play" @click="doRun" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { codingAgentUrl, jsonFetch } from '../services/api'

const modes = ['analyze', 'fix', 'feature', 'tests', 'docs', 'refactor']
const status = ref<any>({})
const jobs = ref<any[]>([])
const runResult = ref<any>(null)
const actionError = ref('')
const loadError = ref('')
const loading = ref(false)
const creating = ref(false)
const confirmDialog = ref(false)
const pendingRunId = ref<string | null>(null)

const form = reactive({
  title: '',
  mode: 'feature',
  prompt: '',
  repo_path: '',
  auto_approve: false,
})

function statusColor(s: string): string {
  const map: Record<string, string> = {
    pending_approval: 'warning',
    queued: 'info',
    running: 'primary',
    completed: 'positive',
    succeeded: 'positive',
    dry_run: 'info',
    failed: 'negative',
  }
  return map[s] ?? 'grey'
}

function describeError(err: unknown): string {
  if (!(err instanceof Error)) return String(err)
  try {
    const i = err.message.indexOf('{')
    if (i >= 0) {
      const payload = JSON.parse(err.message.slice(i))
      const detail = payload.detail ?? payload
      if (detail.reason) return `Blocked: ${detail.reason}`
      if (detail.message) return detail.message
      return JSON.stringify(detail, null, 2)
    }
  } catch {}
  return err.message
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [s, j] = await Promise.all([
      jsonFetch<any>(`${codingAgentUrl}/api/coding-agent/status`),
      jsonFetch<any[]>(`${codingAgentUrl}/api/coding-agent/jobs`),
    ])
    status.value = s
    jobs.value = j
  } catch (err) {
    loadError.value = `Could not reach coding-agent service: ${describeError(err)}`
  } finally {
    loading.value = false
  }
}

async function createJob() {
  if (!form.title || form.title.length < 3) return
  if (!form.prompt || form.prompt.length < 8) return
  creating.value = true
  actionError.value = ''
  runResult.value = null
  try {
    const payload = { ...form, repo_path: form.repo_path || undefined }
    const data = await jsonFetch<any>(`${codingAgentUrl}/api/coding-agent/jobs`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    form.title = ''
    form.prompt = ''
    form.repo_path = ''
    form.auto_approve = false
    runResult.value = { status: data.status, stdout: `Job created: ${data.id}`, stderr: '', artifacts: [] }
    await load()
  } catch (err) {
    actionError.value = describeError(err)
  } finally {
    creating.value = false
  }
}

async function approve(id: string) {
  actionError.value = ''
  try {
    await jsonFetch<any>(`${codingAgentUrl}/api/coding-agent/jobs/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approved_by: 'web' }),
    })
    await load()
  } catch (err) {
    actionError.value = describeError(err)
  }
}

function confirmRun(id: string) {
  pendingRunId.value = id
  confirmDialog.value = true
}

async function doRun() {
  if (!pendingRunId.value) return
  await run(pendingRunId.value, true)
  pendingRunId.value = null
}

async function run(id: string, execute: boolean) {
  actionError.value = ''
  runResult.value = null
  try {
    const data = await jsonFetch<any>(`${codingAgentUrl}/api/coding-agent/jobs/${id}/run`, {
      method: 'POST',
      body: JSON.stringify({ execute }),
    })
    runResult.value = data
    await load()
  } catch (err) {
    actionError.value = describeError(err)
  }
}

onMounted(load)
</script>
