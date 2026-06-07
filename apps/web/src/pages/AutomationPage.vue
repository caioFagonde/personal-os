<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Ops" title="Automation" subtitle="DAG workflows, event triggers, schedules, n8n webhooks, approval gates, side-effect outbox, and notification routing.">
      <template #actions>
        <q-btn color="primary" icon="mdi-refresh" label="Refresh" :loading="loading" @click="refresh" />
      </template>
    </NexusPageHero>

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ error }}
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <q-banner class="glass-card" rounded>
      <template #avatar><q-icon name="mdi-shield-lock-outline" color="warning" /></template>
      Automation is deliberately permissioned. External HTTP, command dispatch, n8n webhooks, destructive nodes, and approval gates require explicit approval.
    </q-banner>

    <div class="row q-col-gutter-md">
      <div class="col-12 col-lg-6">
        <q-card class="glass-card">
          <q-card-section>
            <div class="text-h6 q-mb-sm">Create workflow</div>
            <q-input v-model="workflowName" outlined label="Workflow name" />
            <q-select v-model="workflowKind" outlined :options="workflowKinds" label="Template" class="q-mt-sm" />
            <q-toggle v-model="active" label="Activate immediately" />
          </q-card-section>
          <q-card-actions>
            <q-btn color="primary" unelevated label="Create" icon="mdi-plus" :loading="creating" @click="createWorkflow" />
          </q-card-actions>
        </q-card>
      </div>

      <div class="col-12 col-lg-6">
        <q-card class="glass-card">
          <q-card-section>
            <div class="text-h6 q-mb-sm">Emit event</div>
            <q-input v-model="eventTopic" outlined label="Topic" />
            <q-input v-model="eventPayload" outlined label="Payload JSON" type="textarea" class="q-mt-sm" />
          </q-card-section>
          <q-card-actions>
            <q-btn color="secondary" unelevated label="Emit" icon="mdi-broadcast" :loading="emitting" @click="emitEvent" />
          </q-card-actions>
        </q-card>
      </div>
    </div>

    <q-card class="glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Workflows</div>
      </q-card-section>
      <q-list v-if="workflows.length" separator>
        <q-item v-for="w in workflows" :key="w.id">
          <q-item-section avatar>
            <q-icon name="mdi-transit-connection-variant" />
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ w.name }}</q-item-label>
            <q-item-label caption>
              <q-badge :color="w.active ? 'positive' : 'grey'" :label="w.active ? 'active' : 'inactive'" class="q-mr-xs" />
              approval: {{ w.requires_approval ? 'required' : 'not required' }}
            </q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-btn dense outline color="primary" label="Run" size="sm" @click="runWorkflow(w.id)" />
          </q-item-section>
        </q-item>
      </q-list>
      <NexusEmptyState v-else icon="mdi-transit-connection-variant" message="No workflows yet." hint="Create one above to get started." />
    </q-card>

    <q-card class="glass-card" v-if="runs.length">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Recent runs</div>
      </q-card-section>
      <q-list separator>
        <q-item v-for="r in runs" :key="r.id">
          <q-item-section>
            <q-item-label>
              <q-badge :color="r.status === 'completed' ? 'positive' : r.status === 'failed' ? 'negative' : 'info'" :label="r.status" />
            </q-item-label>
            <q-item-label caption>{{ r.id }} · {{ r.started_at }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <q-card class="glass-card" v-if="events.length">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Recent events</div>
      </q-card-section>
      <q-list separator>
        <q-item v-for="e in events" :key="e.id">
          <q-item-section>
            <q-item-label>{{ e.topic }}</q-item-label>
            <q-item-label caption>{{ e.source }} · seen {{ e.seen_count }}x · {{ e.last_seen_at }}</q-item-label>
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
const loading = ref(false)
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
  loading.value = true
  error.value = ''
  try {
    const [w, r, e] = await Promise.all([
      jsonFetch<any[]>(`${automationUrl}/api/automation/workflows`),
      jsonFetch<any[]>(`${automationUrl}/api/automation/runs`),
      jsonFetch<any[]>(`${automationUrl}/api/automation/events`),
    ])
    workflows.value = w
    runs.value = r
    events.value = e
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function createWorkflow() {
  creating.value = true
  error.value = ''
  try {
    await jsonFetch(`${automationUrl}/api/automation/workflows`, {
      method: 'POST',
      body: JSON.stringify({ spec: templateSpec(), active: active.value }),
    })
    await refresh()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    creating.value = false
  }
}

async function runWorkflow(id: string) {
  error.value = ''
  try {
    await jsonFetch(`${automationUrl}/api/automation/workflows/${id}/runs`, {
      method: 'POST',
      body: JSON.stringify({ input: { source: 'web-ui' } }),
    })
    await refresh()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function emitEvent() {
  emitting.value = true
  error.value = ''
  try {
    await jsonFetch(`${automationUrl}/api/automation/events`, {
      method: 'POST',
      body: JSON.stringify({ topic: eventTopic.value, payload: JSON.parse(eventPayload.value), source: 'web-ui' }),
    })
    await refresh()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    emitting.value = false
  }
}

onMounted(refresh)
</script>
