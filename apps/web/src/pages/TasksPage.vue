<template>
  <q-page class="column q-gutter-lg">

    <NexusPageHero eyebrow="Core Daily" title="Task Inbox" subtitle="Open tasks, delegated work, waiting loops, and completion tracking.">
      <template #actions>
        <q-btn color="primary" unelevated icon="mdi-plus" label="New task" @click="showForm = true" />
        <q-btn outline icon="mdi-refresh" label="Refresh" :loading="loading" @click="load" />
      </template>
    </NexusPageHero>

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      <div>{{ parseErrorMessage(error) }}</div>
      <div v-if="parseErrorAction(error)" class="text-caption q-mt-xs" style="opacity:.85">{{ parseErrorAction(error) }}</div>
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <!-- New task form -->
    <q-card class="glass-card" v-if="showForm">
      <q-card-section>
        <div class="text-h6 q-mb-sm">New task</div>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-8">
            <q-input v-model="form.title" outlined label="Title" autofocus @keydown.enter="createTask" />
          </div>
          <div class="col-12 col-md-4">
            <q-select v-model="form.priority" outlined :options="priorities" label="Priority" option-label="label" option-value="value" emit-value map-options />
          </div>
          <div class="col-12">
            <q-input v-model="form.body" outlined type="textarea" autogrow label="Notes (optional)" />
          </div>
        </div>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat label="Cancel" @click="showForm = false; clearForm()" />
        <q-btn color="primary" icon="mdi-check" label="Create task" :loading="creating" @click="createTask" />
      </q-card-actions>
    </q-card>

    <!-- Filter tabs -->
    <q-card class="glass-card">
      <q-tabs v-model="filter" dense align="left" no-caps active-color="primary" indicator-color="primary">
        <q-tab name="inbox"     label="Inbox"     />
        <q-tab name="delegated" label="Delegated" />
        <q-tab name="all"       label="All"       />
      </q-tabs>
      <q-separator dark />
      <q-card-section v-if="loading && !tasks.length">
        <q-inner-loading showing color="primary" />
      </q-card-section>
      <q-list separator v-else-if="filteredTasks.length">
        <q-item v-for="task in filteredTasks" :key="task.id" class="q-py-md">
          <q-item-section avatar>
            <q-icon
              :name="task.status === 'delegated' ? 'mdi-account-arrow-right' : task.status === 'completed' ? 'mdi-check-circle-outline' : 'mdi-checkbox-blank-circle-outline'"
              :color="task.status === 'completed' ? 'positive' : task.status === 'delegated' ? 'info' : 'grey'"
            />
          </q-item-section>
          <q-item-section>
            <q-item-label :class="task.status === 'completed' ? 'text-strike text-muted' : ''">{{ task.title }}</q-item-label>
            <q-item-label caption>
              <q-badge :color="priorityColor(task.priority)" :label="`p${task.priority}`" class="q-mr-xs" />
              {{ task.status }}
              <span v-if="task.assignee_key"> · {{ task.assignee_key }}</span>
              <span v-if="task.due_at"> · due {{ formatDate(task.due_at) }}</span>
            </q-item-label>
          </q-item-section>
          <q-item-section side>
            <div class="row q-gutter-xs">
              <q-btn
                v-if="task.status !== 'completed'"
                flat round size="sm"
                icon="mdi-folder-star-outline"
                color="primary"
                :title="'Assign to project'"
                :data-testid="`task-assign-${task.id}`"
              >
                <q-menu auto-close>
                  <q-list dense style="min-width: 220px">
                    <q-item-label header>Assign to project</q-item-label>
                    <q-item v-for="project in projects" :key="project.id" clickable @click="assignProject(task.id, project.id)">
                      <q-item-section>{{ project.name }}</q-item-section>
                    </q-item>
                    <q-item v-if="!projects.length">
                      <q-item-section class="text-caption">No projects yet — create one on the Projects page.</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
              </q-btn>
              <q-btn
                v-if="task.status !== 'completed'"
                flat round size="sm"
                icon="mdi-check"
                color="positive"
                @click="complete(task.id)"
                :title="'Mark complete'"
              />
            </div>
          </q-item-section>
        </q-item>
      </q-list>
      <q-card-section v-else>
        <div class="text-muted text-center q-py-lg">
          <q-icon name="mdi-checkbox-marked-circle-outline" size="48px" style="opacity:.3" /><br>
          No tasks in this view.
        </div>
      </q-card-section>
    </q-card>

  </q-page>
</template>

<script setup lang="ts">
import { onMounted, computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { captureUrl, jsonFetch, moduleUrl } from '../services/api'

function parseErrorMessage(raw: string): string {
  try {
    const idx = raw.indexOf('{')
    if (idx >= 0) {
      const parsed = JSON.parse(raw.slice(idx))
      const detail = parsed.detail || parsed.error
      if (detail && typeof detail === 'object') return detail.message || raw
    }
  } catch { /* not JSON */ }
  return raw
}

function parseErrorAction(raw: string): string {
  try {
    const idx = raw.indexOf('{')
    if (idx >= 0) {
      const parsed = JSON.parse(raw.slice(idx))
      const detail = parsed.detail || parsed.error
      if (detail && typeof detail === 'object') return detail.action || ''
    }
  } catch { /* not JSON */ }
  return ''
}

const tasks = ref<any[]>([])
const loading = ref(false)
const creating = ref(false)
const error = ref('')
const showForm = ref(false)
const filter = ref('inbox')

const priorities = [
  { label: 'P1 — Urgent', value: 1 },
  { label: 'P2 — High',   value: 2 },
  { label: 'P3 — Normal', value: 3 },
  { label: 'P4 — Low',    value: 4 },
  { label: 'P5 — Someday', value: 5 },
]

const form = reactive({ title: '', body: '', priority: 3 })

const filteredTasks = computed(() => {
  if (filter.value === 'inbox') return tasks.value.filter(t => t.status === 'inbox')
  if (filter.value === 'delegated') return tasks.value.filter(t => t.status === 'delegated')
  return tasks.value
})

function priorityColor(p: number): string {
  return ['', 'negative', 'warning', 'primary', 'grey', 'grey-6'][p] ?? 'grey'
}

function formatDate(iso: string): string {
  try { return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) } catch { return iso }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    tasks.value = await jsonFetch<any[]>(`${captureUrl}/api/tasks`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function createTask() {
  if (!form.title.trim()) return
  creating.value = true
  error.value = ''
  try {
    await jsonFetch<any>(`${captureUrl}/api/tasks`, {
      method: 'POST',
      body: JSON.stringify({ title: form.title, body: form.body, priority: form.priority, source_kind: 'manual' }),
    })
    clearForm()
    showForm.value = false
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    creating.value = false
  }
}

async function complete(id: string) {
  error.value = ''
  try {
    await jsonFetch<any>(`${captureUrl}/api/tasks/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: 'completed' }),
    })
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

const projects = ref<any[]>([])

async function loadProjects() {
  try {
    projects.value = await jsonFetch<any[]>(`${moduleUrl}/api/projects?status=active`)
  } catch {
    projects.value = [] // menu shows its empty state; tasks stay fully usable
  }
}

async function assignProject(taskId: string, projectId: string) {
  error.value = ''
  try {
    await jsonFetch<any>(`${captureUrl}/api/tasks/${taskId}`, {
      method: 'PATCH',
      body: JSON.stringify({ project_id: projectId }),
    })
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

function clearForm() {
  form.title = ''
  form.body = ''
  form.priority = 3
}

watch(filter, load)
const route = useRoute()
onMounted(() => {
  if (route.query.new === '1') showForm.value = true // palette "New task" action
  void load()
  void loadProjects()
})
</script>
