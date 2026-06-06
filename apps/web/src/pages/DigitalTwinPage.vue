<template>
  <q-page class="digital-twin-page">
    <section class="twin-hero glass-panel q-pa-lg q-pa-md-xl">
      <div class="row items-center q-col-gutter-xl">
        <div class="col-12 col-lg-7">
          <div class="text-overline text-purple-2">Phase 8 · Personal intelligence layer</div>
          <h1 class="twin-title">A privacy-aware model of your goals, state, memory, and next best actions.</h1>
          <p class="twin-subtitle">
            The Digital Twin synthesizes timeline events, state snapshots, goals, and memory policies into recommendations that remain local-first, auditable, and approval-gated.
          </p>
          <div class="row q-gutter-sm q-mt-lg">
            <q-btn rounded unelevated color="primary" icon="mdi-brain" label="Refresh twin" @click="load" />
            <q-btn rounded outline color="purple-2" icon="mdi-lightbulb-on-outline" label="Generate recommendations" @click="recommend" />
            <q-btn rounded outline color="cyan-2" icon="mdi-shield-lock-outline" label="Load policy" @click="loadPolicy" />
          </div>
        </div>
        <div class="col-12 col-lg-5">
          <div class="signal-grid">
            <MetricCard label="Timeline events" :value="timeline.summary?.event_count ?? 0" icon="mdi-timeline-clock-outline" />
            <MetricCard label="State confidence" :value="confidenceLabel" icon="mdi-chart-bell-curve" />
            <MetricCard label="Recommendations" :value="recommendations.length" icon="mdi-lightbulb-on-outline" />
          </div>
        </div>
      </div>
    </section>

    <section class="q-mt-lg row q-col-gutter-md">
      <div class="col-12 col-lg-4">
        <q-card class="glass-panel" flat>
          <q-card-section>
            <div class="text-h6">Add signal</div>
            <div class="text-caption text-blue-grey-3">Record a timeline event or state observation.</div>
          </q-card-section>
          <q-card-section class="q-gutter-md">
            <q-input v-model="eventType" dark outlined label="Event type" placeholder="study.session.completed" />
            <q-input v-model="eventDomain" dark outlined label="Domain" placeholder="learning" />
            <q-slider v-model="importance" :min="0" :max="1" :step="0.05" label label-always color="primary" />
            <q-btn class="full-width" unelevated rounded color="primary" icon="mdi-plus" label="Record event" @click="recordEvent" />
          </q-card-section>
        </q-card>

        <q-card class="glass-panel q-mt-md" flat>
          <q-card-section>
            <div class="text-h6">Goal vector</div>
            <div class="text-caption text-blue-grey-3">Feed the recommendation engine with concrete intent.</div>
          </q-card-section>
          <q-card-section class="q-gutter-md">
            <q-input v-model="goalTitle" dark outlined label="Goal" placeholder="Master Bayesian filtering" />
            <q-input v-model="goalDomain" dark outlined label="Domain" placeholder="learning" />
            <q-slider v-model="goalPriority" :min="0" :max="100" :step="5" label label-always color="purple" />
            <q-btn class="full-width" rounded outline color="purple-2" icon="mdi-target" label="Create goal" @click="createGoal" />
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-lg-8">
        <q-card class="glass-panel" flat>
          <q-card-section class="row items-center justify-between">
            <div>
              <div class="text-h6">Next best actions</div>
              <div class="text-caption text-blue-grey-3">Deterministic, explainable recommendations from current state.</div>
            </div>
            <q-chip color="primary" text-color="dark" :label="`${recommendations.length} active`" />
          </q-card-section>
          <q-card-section>
            <div v-if="!recommendations.length" class="empty-state q-pa-lg text-center">
              <q-icon name="mdi-lightbulb-on-outline" size="54px" />
              <div class="text-subtitle1 q-mt-sm">No recommendations loaded.</div>
              <div class="text-caption text-blue-grey-3">Generate a run after adding events or goals.</div>
            </div>
            <q-list v-else separator>
              <q-item v-for="rec in recommendations" :key="rec.id" class="recommendation-item">
                <q-item-section avatar>
                  <q-avatar :color="rec.requires_approval ? 'warning' : 'primary'" text-color="dark" icon="mdi-lightning-bolt" />
                </q-item-section>
                <q-item-section>
                  <q-item-label class="text-weight-bold">{{ rec.title }}</q-item-label>
                  <q-item-label caption>{{ rec.rationale }}</q-item-label>
                  <div class="row q-gutter-xs q-mt-sm">
                    <q-chip dense outline>{{ rec.domain }}</q-chip>
                    <q-chip dense outline>priority {{ rec.priority }}</q-chip>
                    <q-chip dense outline>{{ Math.round(rec.confidence * 100) }}% confidence</q-chip>
                    <q-chip v-if="rec.requires_approval" dense color="warning" text-color="dark">approval</q-chip>
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>

        <div class="row q-col-gutter-md q-mt-md">
          <div class="col-12 col-md-6">
            <q-card class="glass-panel" flat>
              <q-card-section>
                <div class="text-h6">Inferred state</div>
                <pre class="state-code">{{ JSON.stringify(state.state || {}, null, 2) }}</pre>
              </q-card-section>
            </q-card>
          </div>
          <div class="col-12 col-md-6">
            <q-card class="glass-panel" flat>
              <q-card-section>
                <div class="text-h6">Memory policy</div>
                <pre class="state-code">{{ JSON.stringify(policy.policy || {}, null, 2) }}</pre>
              </q-card-section>
            </q-card>
          </div>
        </div>
      </div>
    </section>

    <section class="q-mt-lg">
      <q-card class="glass-panel" flat>
        <q-card-section class="row items-center justify-between">
          <div>
            <div class="text-h6">Timeline</div>
            <div class="text-caption text-blue-grey-3">Most recent events feeding the model.</div>
          </div>
          <q-btn flat color="cyan-2" icon="mdi-refresh" label="Reload" @click="load" />
        </q-card-section>
        <q-card-section>
          <q-timeline color="primary">
            <q-timeline-entry v-for="event in timeline.events || []" :key="event.id" :title="event.event_type" :subtitle="event.occurred_at">
              <div class="text-caption text-blue-grey-3">{{ (event.domains || []).join(', ') }} · importance {{ event.importance }}</div>
            </q-timeline-entry>
          </q-timeline>
        </q-card-section>
      </q-card>
    </section>
    <q-banner v-if="error" class="bg-negative text-white q-mt-md rounded-borders">{{ error }}</q-banner>
  </q-page>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import MetricCard from '../components/MetricCard.vue'
import { digitalTwinUrl, jsonFetch } from '../services/api'

const timeline = ref<any>({ events: [], summary: {} })
const state = ref<any>({ state: {} })
const policy = ref<any>({ policy: {} })
const goals = ref<any[]>([])
const recommendations = ref<any[]>([])
const error = ref('')
const eventType = ref('study.session.completed')
const eventDomain = ref('learning')
const importance = ref(0.7)
const goalTitle = ref('')
const goalDomain = ref('learning')
const goalPriority = ref(80)
const confidenceLabel = computed(() => `${Math.round((state.value.state?.confidence || 0) * 100)}%`)

async function load() {
  error.value = ''
  try {
    const [tl, inferred, gs] = await Promise.all([
      jsonFetch<any>(`${digitalTwinUrl}/api/digital-twin/timeline?limit=50`),
      jsonFetch<any>(`${digitalTwinUrl}/api/digital-twin/state/infer`),
      jsonFetch<any[]>(`${digitalTwinUrl}/api/digital-twin/goals`)
    ])
    timeline.value = tl
    state.value = inferred
    goals.value = gs
  } catch (e: any) { error.value = e.message }
}
async function loadPolicy() {
  try { policy.value = await jsonFetch<any>(`${digitalTwinUrl}/api/digital-twin/memory/policy`) } catch (e: any) { error.value = e.message }
}
async function recordEvent() {
  await jsonFetch(`${digitalTwinUrl}/api/digital-twin/events`, {
    method: 'POST',
    body: JSON.stringify({ event_type: eventType.value, payload: { domain: eventDomain.value, importance: importance.value } })
  })
  await load()
}
async function createGoal() {
  if (!goalTitle.value.trim()) return
  await jsonFetch(`${digitalTwinUrl}/api/digital-twin/goals`, {
    method: 'POST',
    body: JSON.stringify({ title: goalTitle.value, domain: goalDomain.value, priority: goalPriority.value, progress: 0 })
  })
  goalTitle.value = ''
  await load()
}
async function recommend() {
  const result = await jsonFetch<any>(`${digitalTwinUrl}/api/digital-twin/recommendations`, {
    method: 'POST',
    body: JSON.stringify({ state: state.value.state, goals: goals.value, persist: true })
  })
  recommendations.value = result.recommendations || []
}
onMounted(async () => { await Promise.all([load(), loadPolicy()]) })
</script>
<style scoped>
.twin-title { font-size: clamp(34px, 6vw, 76px); line-height: .94; margin: 0; max-width: 1000px; }
.twin-subtitle { color: var(--nexus-muted); font-size: clamp(16px, 2vw, 20px); max-width: 780px; }
.signal-grid { display: grid; gap: 14px; }
.state-code { white-space: pre-wrap; color: #d7e7ff; background: rgba(2, 8, 23, .42); border-radius: 16px; padding: 16px; max-height: 320px; overflow: auto; }
.recommendation-item { border-radius: 18px; margin-bottom: 8px; background: rgba(255,255,255,.035); }
.empty-state { color: var(--nexus-muted); }
</style>
