<template>
  <q-page padding>
    <div class="row items-center q-col-gutter-md">
      <div class="col-12 col-md-8">
        <h1>Automation</h1>
        <p>DAG workflows, event triggers, schedules, n8n webhooks, approval gates, side-effect outbox, and notification routing.</p>
      </div>
      <div class="col-12 col-md-4 text-right">
        <q-btn color="primary" label="Refresh" @click="refresh" />
      </div>
    </div>

    <q-banner class="bg-warning text-dark q-mb-md">
      Automation is deliberately permissioned. External HTTP, command dispatch, n8n webhooks, destructive nodes, and approval gates require explicit approval.
    </q-banner>

    <div class="row q-col-gutter-md">
      <div class="col-12 col-lg-6">
        <q-card bordered flat>
          <q-card-section>
            <div class="text-h6">Create workflow</div>
            <q-input v-model="workflowName" label="Workflow name" dense outlined />
            <q-select v-model="workflowKind" :options="workflowKinds" label="Template" dense outlined class="q-mt-sm" />
            <q-toggle v-model="active" label="Activate immediately" />
          </q-card-section>
          <q-card-actions>
            <q-btn color="primary" label="Create" :loading="creating" @click="createWorkflow" />
          </q-card-actions>
        </q-card>
      </div>

      <div class="col-12 col-lg-6">
        <q-card bordered flat>
          <q-card-section>
            <div class="text-h6">Emit event</div>
            <q-input v-model="eventTopic" label="Topic" dense outlined />
            <q-input v-model="eventPayload" label="Payload JSON" type="textarea" dense outlined class="q-mt-sm" />
          </q-card-section>
          <q-card-actions>
            <q-btn color="secondary" label="Emit" :loading="emitting" @click="emitEvent" />
          </q-card-actions>
        </q-card>
      </div>
    </div>

    <q-banner v-if="error" class="bg-negative text-white q-mt-md">{{ error }}</q-banner>

    <h2 class="q-mt-xl">Workflows</h2>
    <q-list bordered separator>
      <q-item v-for="w in workflows" :key="w.id">
        <q-item-section>
          <q-item-label>{{ w.name }}</q-item-label>
          <q-item-label caption>{{ w.active ? 'active' : 'inactive' }} · approval: {{ w.requires_approval ? 'required' : 'not required' }}</q-item-label>
        </q-item-section>
        <q-item-section side>
          <q-btn dense outline color="primary" label="Run" @click="runWorkflow(w.id)" />
        </q-item-section>
      </q-item>
    </q-list>

    <h2 class="q-mt-xl">Recent runs</h2>
    <q-list bordered separator>
      <q-item v-for="r in runs" :key="r.id">
        <q-item-section>
          <q-item-label>{{ r.status }}</q-item-label>
          <q-item-label caption>{{ r.id }} · {{ r.started_at }}</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>

    <h2 class="q-mt-xl">Recent events</h2>
    <q-list bordered separator>
      <q-item v-for="e in events" :key="e.id">
        <q-item-section>
          <q-item-label>{{ e.topic }}</q-item-label>
          <q-item-label caption>{{ e.source }} · seen {{ e.seen_count }}x · {{ e.last_seen_at }}</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>
  </q-page>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { automationUrl, jsonFetch } from '../services/api'

const workflows = ref<any[]>([])
const runs = ref<any[]>([])
const events = ref<any[]>([])
const workflowName = ref('Daily study completion notification')
const workflowKind = ref('notification')
const workflowKinds = ['notification', 'approval-gated-command', 'event-to-artifact']
const active = ref(true)
const eventTopic = ref('study.session.completed')
const eventPayload = ref('{"minutes":45,"subject":"mathematics"}')
const creating = ref(false)
const emitting = ref(false)
const error = ref('')

function templateSpec() {
  if (workflowKind.value === 'approval-gated-command') {
    return {
      name: workflowName.value,
      triggers: [{ type: 'manual' }],
      nodes: [
        { id: 'gate', type: 'approval_gate' },
        { id: 'cmd', type: 'command_request', config: { template_id: 'coding_harness' }, scopes: ['command:request'] }
      ],
      edges: [{ from: 'gate', to: 'cmd' }]
    }
  }
  if (workflowKind.value === 'event-to-artifact') {
    return {
      name: workflowName.value,
      triggers: [{ type: 'event', topic: 'research.document.ingested' }],
      nodes: [
        { id: 'transform', type: 'transform', config: { output: { kind: 'summary-request' } } },
        { id: 'artifact', type: 'artifact', config: { artifact: { type: 'markdown', name: 'summary.md' } } }
      ],
      edges: [{ from: 'transform', to: 'artifact' }]
    }
  }
  return {
    name: workflowName.value,
    triggers: [{ type: 'event', topic: 'study.session.completed' }],
    nodes: [
      { id: 'format', type: 'transform', config: { output: { title: 'Study session completed' } } },
      { id: 'notify', type: 'notification', config: { topic: 'personal-os-dev', title: 'Study complete', message: 'Logged study session.' }, scopes: ['notifications:send'] }
    ],
    edges: [{ from: 'format', to: 'notify' }]
  }
}

async function refresh() {
  error.value = ''
  try {
    workflows.value = await jsonFetch<any[]>(`${automationUrl}/api/automation/workflows`)
    runs.value = await jsonFetch<any[]>(`${automationUrl}/api/automation/runs`)
    events.value = await jsonFetch<any[]>(`${automationUrl}/api/automation/events`)
  } catch (e: any) { error.value = e.message }
}

async function createWorkflow() {
  creating.value = true
  error.value = ''
  try {
    await jsonFetch(`${automationUrl}/api/automation/workflows`, {
      method: 'POST',
      body: JSON.stringify({ spec: templateSpec(), active: active.value })
    })
    await refresh()
  } catch (e: any) { error.value = e.message } finally { creating.value = false }
}

async function runWorkflow(id: string) {
  error.value = ''
  try {
    await jsonFetch(`${automationUrl}/api/automation/workflows/${id}/runs`, {
      method: 'POST',
      body: JSON.stringify({ input: { source: 'web-ui' } })
    })
    await refresh()
  } catch (e: any) { error.value = e.message }
}

async function emitEvent() {
  emitting.value = true
  error.value = ''
  try {
    await jsonFetch(`${automationUrl}/api/automation/events`, {
      method: 'POST',
      body: JSON.stringify({ topic: eventTopic.value, payload: JSON.parse(eventPayload.value), source: 'web-ui' })
    })
    await refresh()
  } catch (e: any) { error.value = e.message } finally { emitting.value = false }
}

onMounted(refresh)
</script>
