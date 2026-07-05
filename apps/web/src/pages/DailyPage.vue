<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Core Daily" title="Today / Focus" subtitle="Open the day with an intention, work the focus list, close with a review. Everything logs into the graph.">
      <template #actions>
        <q-btn unelevated color="primary" icon="mdi-lightning-bolt-outline" label="Capture" to="/capture" />
        <q-btn outline icon="mdi-refresh" label="Refresh" :loading="loading" @click="load" />
      </template>
    </NexusPageHero>

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ error }}
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <!-- Today -->
    <q-card class="glass-card" data-testid="daily-today">
      <q-card-section>
        <div class="row items-center justify-between">
          <div class="text-h6">Today · {{ today.day }}</div>
          <q-badge v-if="today.opened" :color="today.closed ? 'primary' : 'positive'" :label="today.closed ? 'closed' : 'open'" />
          <q-badge v-else color="grey" label="not opened" />
        </div>

        <!-- Not opened yet -->
        <div v-if="!today.opened" class="q-mt-md column q-gutter-md">
          <q-input v-model="intention" outlined label="Intention — what makes today a win?" data-testid="daily-intention" />
          <q-btn color="primary" unelevated icon="mdi-weather-sunset-up" label="Open day" :loading="saving" @click="openDay" data-testid="daily-open" />
        </div>

        <!-- Open, not closed -->
        <div v-else-if="!today.closed" class="q-mt-md column q-gutter-md">
          <p v-if="today.intention"><q-icon name="mdi-target" size="16px" /> {{ today.intention }}</p>
          <q-input v-model="review" outlined type="textarea" autogrow label="Review — how did it go?" data-testid="daily-review" />
          <q-input v-model="highlightText" outlined label="Highlights, comma-separated" />
          <div class="row q-col-gutter-md">
            <div class="col-6">
              <div class="text-caption q-mb-xs">Energy (optional)</div>
              <q-rating v-model="energy" :max="5" icon="mdi-battery-outline" icon-selected="mdi-battery" color="positive" size="1.5em" />
            </div>
            <div class="col-6">
              <div class="text-caption q-mb-xs">Mood (optional)</div>
              <q-rating v-model="mood" :max="5" icon="mdi-emoticon-neutral-outline" icon-selected="mdi-emoticon-happy" color="warning" size="1.5em" />
            </div>
          </div>
          <q-btn color="primary" unelevated icon="mdi-weather-night" label="Close day" :loading="saving" @click="closeDay" data-testid="daily-close" />
        </div>

        <!-- Closed -->
        <div v-else class="q-mt-md">
          <p v-if="today.intention"><q-icon name="mdi-target" size="16px" /> {{ today.intention }}</p>
          <p v-if="today.review">{{ today.review }}</p>
          <div class="row q-gutter-xs" v-if="(today.highlights || []).length">
            <q-chip v-for="h in today.highlights" :key="h" dense outline size="sm" icon="mdi-star-outline">{{ h }}</q-chip>
          </div>
          <div class="text-caption q-mt-sm" style="color:var(--nexus-muted)">
            <span v-if="today.energy">energy {{ today.energy }}/5 · </span>
            <span v-if="today.mood">mood {{ today.mood }}/5 · </span>
            Day closed. See you tomorrow.
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Focus list: due, overdue, and top-priority inbox tasks -->
    <q-card class="glass-card" data-testid="today-focus">
      <q-card-section>
        <div class="row items-center justify-between">
          <div class="text-h6">Focus</div>
          <q-btn flat color="primary" size="sm" label="All tasks" to="/tasks" icon-right="mdi-arrow-right" />
        </div>
      </q-card-section>
      <q-separator dark />
      <q-list separator v-if="focusTasks.length">
        <q-item v-for="task in focusTasks" :key="task.id">
          <q-item-section avatar>
            <q-icon
              :name="isOverdue(task) ? 'mdi-alert-circle-outline' : 'mdi-checkbox-blank-circle-outline'"
              :color="isOverdue(task) ? 'negative' : 'grey'"
            />
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ task.title }}</q-item-label>
            <q-item-label caption>
              <q-badge :color="isOverdue(task) ? 'negative' : 'primary'" :label="`p${task.priority}`" class="q-mr-xs" />
              <span v-if="task.due_at">{{ isOverdue(task) ? 'overdue' : 'due' }} {{ formatDue(task.due_at) }}</span>
              <span v-else>no due date</span>
            </q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-btn flat round size="sm" icon="mdi-check" color="positive" title="Mark complete" @click="completeTask(task.id)" />
          </q-item-section>
        </q-item>
      </q-list>
      <q-card-section v-else>
        <div class="text-center q-py-md" style="color:var(--nexus-muted)">
          Nothing due or in the inbox. Capture something or enjoy the quiet.
        </div>
      </q-card-section>
    </q-card>

    <!-- History -->
    <q-card class="glass-card" v-if="history.length">
      <q-card-section>
        <div class="text-h6 q-mb-sm">Recent days</div>
        <q-list separator>
          <q-item v-for="day in history" :key="day.id">
            <q-item-section avatar>
              <q-icon :name="day.closed ? 'mdi-check-circle-outline' : 'mdi-progress-clock'" :color="day.closed ? 'positive' : 'warning'" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ day.day }}</q-item-label>
              <q-item-label caption>
                <span v-if="day.intention">{{ day.intention }}</span>
                <span v-if="day.review"> · {{ day.review.slice(0, 100) }}</span>
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="text-caption" style="color:var(--nexus-muted)">
                <span v-if="day.energy">⚡{{ day.energy }}</span>
                <span v-if="day.mood"> ☺{{ day.mood }}</span>
              </div>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
import { captureUrl, jsonFetch, moduleUrl } from '../services/api'

interface DailyState {
  id?: string
  day: string
  intention?: string
  highlights?: string[]
  energy?: number | null
  mood?: number | null
  review?: string
  opened: boolean
  closed: boolean
}

const today = ref<DailyState>({ day: new Date().toISOString().slice(0, 10), opened: false, closed: false })
const history = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const intention = ref('')
const review = ref('')
const highlightText = ref('')
const energy = ref(0)
const mood = ref(0)

interface FocusTask {
  id: string
  title: string
  status: string
  priority: number
  due_at: string | null
}

const tasks = ref<FocusTask[]>([])

const focusTasks = computed(() => {
  const open = tasks.value.filter(t => !['completed', 'archived'].includes(t.status))
  const dued = open.filter(t => t.due_at)
  const rest = open.filter(t => !t.due_at).sort((a, b) => a.priority - b.priority)
  const ordered = [...dued.sort((a, b) => String(a.due_at).localeCompare(String(b.due_at))), ...rest]
  return ordered.slice(0, 8)
})

function isOverdue(task: FocusTask): boolean {
  return !!task.due_at && new Date(task.due_at).getTime() < Date.now()
}

function formatDue(iso: string): string {
  try { return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) } catch { return iso }
}

async function completeTask(id: string) {
  try {
    await jsonFetch(`${captureUrl}/api/tasks/${id}`, { method: 'PATCH', body: JSON.stringify({ status: 'completed' }) })
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    today.value = await jsonFetch<DailyState>(`${moduleUrl}/api/daily-state/today`)
    history.value = await jsonFetch<any[]>(`${moduleUrl}/api/daily-state?limit=14`)
    tasks.value = await jsonFetch<FocusTask[]>(`${captureUrl}/api/tasks`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function openDay() {
  saving.value = true
  error.value = ''
  try {
    await jsonFetch(`${moduleUrl}/api/daily-state/open`, {
      method: 'POST',
      body: JSON.stringify({ intention: intention.value }),
    })
    intention.value = ''
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    saving.value = false
  }
}

async function closeDay() {
  saving.value = true
  error.value = ''
  try {
    await jsonFetch(`${moduleUrl}/api/daily-state/close`, {
      method: 'POST',
      body: JSON.stringify({
        review: review.value,
        highlights: highlightText.value.split(',').map(s => s.trim()).filter(Boolean),
        energy: energy.value || null,
        mood: mood.value || null,
      }),
    })
    review.value = ''
    highlightText.value = ''
    energy.value = 0
    mood.value = 0
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
