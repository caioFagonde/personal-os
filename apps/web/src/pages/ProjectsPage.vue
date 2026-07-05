<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Core Daily" title="Projects" subtitle="Active initiatives — every task, note, and decision hangs off one of these.">
      <template #actions>
        <q-btn color="primary" unelevated icon="mdi-plus" label="New project" @click="showForm = true" />
        <q-btn outline icon="mdi-refresh" label="Refresh" :loading="loading" @click="load" />
      </template>
    </NexusPageHero>

    <q-banner v-if="error" class="bg-negative text-white" rounded>
      <template #avatar><q-icon name="mdi-alert-circle-outline" /></template>
      {{ error }}
      <template #action><q-btn flat color="white" label="Dismiss" @click="error = ''" /></template>
    </q-banner>

    <q-card class="glass-card" v-if="showForm">
      <q-card-section>
        <div class="text-h6 q-mb-sm">New project</div>
        <div class="column q-gutter-md">
          <q-input v-model="form.name" outlined label="Name" autofocus data-testid="project-name" />
          <q-input v-model="form.pitch" outlined label="Pitch — what is this, in one sentence?" />
          <q-input v-model="form.north_star" outlined label="North star — what does done look like?" />
        </div>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat label="Cancel" @click="showForm = false" />
        <q-btn color="primary" icon="mdi-check" label="Create project" :loading="creating" @click="createProject" data-testid="project-create" />
      </q-card-actions>
    </q-card>

    <div v-if="loading && !projects.length" class="text-center q-py-xl">
      <q-spinner color="primary" size="40px" />
    </div>

    <div v-else-if="projects.length" class="module-grid">
      <q-card v-for="project in projects" :key="project.id" class="glass-card" :data-testid="`project-card-${project.slug}`">
        <q-card-section>
          <div class="row items-center justify-between">
            <div class="text-h6">{{ project.name }}</div>
            <q-badge :color="statusColor(project.status)" :label="project.status" />
          </div>
          <div class="text-caption" style="color:var(--nexus-muted)">{{ project.slug }}</div>
          <p v-if="project.pitch" class="q-mt-sm" style="color:var(--nexus-muted);font-size:13px">{{ project.pitch }}</p>
          <p v-if="project.north_star" class="text-caption"><q-icon name="mdi-star-four-points-outline" size="14px" /> {{ project.north_star }}</p>
        </q-card-section>
        <q-card-actions>
          <q-btn flat color="primary" size="sm" label="Open" @click="openProject(project)" />
          <q-btn v-if="project.status === 'active'" flat size="sm" label="Pause" @click="setStatus(project, 'paused')" />
          <q-btn v-else-if="project.status === 'paused'" flat size="sm" label="Resume" @click="setStatus(project, 'active')" />
          <q-btn v-if="project.status !== 'done'" flat color="positive" size="sm" label="Mark done" @click="setStatus(project, 'done')" />
        </q-card-actions>
      </q-card>
    </div>

    <NexusEmptyState v-else icon="mdi-folder-star-outline" message="No projects yet." hint="Create your first project — tasks and notes will link into it." />

    <q-dialog v-model="dialog">
      <q-card class="glass-card" style="min-width: min(720px, 92vw)">
        <q-card-section v-if="selected">
          <div class="row items-center justify-between">
            <div class="text-h6">{{ selected.name }}</div>
            <q-badge :color="statusColor(selected.status)" :label="selected.status" />
          </div>
          <p v-if="selected.pitch" class="q-mt-sm">{{ selected.pitch }}</p>
          <p v-if="selected.north_star" class="text-caption"><q-icon name="mdi-star-four-points-outline" size="14px" /> {{ selected.north_star }}</p>
        </q-card-section>
        <q-separator />
        <q-card-section>
          <div class="text-subtitle2 q-mb-xs">Linked in graph</div>
          <div v-if="neighborsLoading" class="q-py-md text-center"><q-spinner color="primary" size="24px" /></div>
          <q-list v-else-if="neighbors.length" dense data-testid="project-neighbors">
            <q-item v-for="n in neighbors" :key="n.object.id">
              <q-item-section avatar><q-icon :name="kindIcons[n.object.kind] ?? 'mdi-shape-outline'" size="18px" /></q-item-section>
              <q-item-section>
                <q-item-label>{{ n.object.title || n.object.kind }}</q-item-label>
                <q-item-label caption>{{ n.rel }} · {{ n.object.kind }}<span v-if="n.object.status"> · {{ n.object.status }}</span></q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
          <div v-else class="text-caption" style="color:var(--nexus-muted)">
            Nothing linked yet. Assign tasks to this project from the Task Inbox.
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Close" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import NexusPageHero from '../components/NexusPageHero.vue'
import NexusEmptyState from '../components/NexusEmptyState.vue'
import { jsonFetch, moduleUrl } from '../services/api'
import { graphNeighbors, kindIcons, type GraphNeighbor } from '../services/graph'

interface Project {
  id: string
  name: string
  slug: string
  status: string
  pitch: string
  north_star: string
  object_id?: string | null
}

const route = useRoute()
const projects = ref<Project[]>([])
const loading = ref(false)
const creating = ref(false)
const error = ref('')
const showForm = ref(false)
const dialog = ref(false)
const selected = ref<Project | null>(null)
const neighbors = ref<GraphNeighbor[]>([])
const neighborsLoading = ref(false)
const form = reactive({ name: '', pitch: '', north_star: '' })

function statusColor(status: string): string {
  return { active: 'positive', paused: 'warning', done: 'primary', archived: 'grey' }[status] ?? 'grey'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    projects.value = await jsonFetch<Project[]>(`${moduleUrl}/api/projects`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function createProject() {
  if (!form.name.trim()) return
  creating.value = true
  error.value = ''
  try {
    await jsonFetch(`${moduleUrl}/api/projects`, {
      method: 'POST',
      body: JSON.stringify({ name: form.name, pitch: form.pitch, north_star: form.north_star }),
    })
    form.name = ''
    form.pitch = ''
    form.north_star = ''
    showForm.value = false
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    creating.value = false
  }
}

async function setStatus(project: Project, status: string) {
  error.value = ''
  try {
    await jsonFetch(`${moduleUrl}/api/projects/${project.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    })
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function openProject(project: Project) {
  selected.value = project
  dialog.value = true
  neighbors.value = []
  neighborsLoading.value = true
  try {
    const detail = await jsonFetch<Project>(`${moduleUrl}/api/projects/${project.id}`)
    if (detail.object_id) neighbors.value = await graphNeighbors(detail.object_id)
  } catch {
    // neighbors are enrichment; the dialog stays useful without them
  } finally {
    neighborsLoading.value = false
  }
}

onMounted(async () => {
  if (route.query.new === '1') showForm.value = true // palette "New project" action
  await load()
  const openId = route.query.open
  if (typeof openId === 'string') {
    const match = projects.value.find(p => p.id === openId)
    if (match) await openProject(match)
  }
})
</script>
