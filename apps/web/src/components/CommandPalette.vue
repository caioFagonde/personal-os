<template>
  <q-dialog v-model="open" maximized transition-show="jump-down" transition-hide="jump-up">
    <q-card class="command-palette glass-panel">
      <q-card-section class="row items-center q-gutter-sm">
        <q-icon name="mdi-command" size="28px" />
        <q-input
          v-model="query"
          autofocus
          borderless
          placeholder="Search actions, modules, notes, tasks, projects…"
          class="col"
          @keydown.down.prevent="move(1)"
          @keydown.up.prevent="move(-1)"
          @keydown.enter.prevent="runSelected"
          @keydown.esc="open = false"
        />
        <q-btn flat round icon="mdi-close" @click="open = false" />
      </q-card-section>
      <q-separator />
      <q-list class="command-palette__results">
        <template v-for="(section, sIdx) in sections" :key="section.title">
          <q-item-label v-if="section.entries.length" header class="text-caption">{{ section.title }}</q-item-label>
          <q-item
            v-for="(entry, eIdx) in section.entries"
            :key="entry.key"
            clickable
            :active="isSelected(sIdx, eIdx)"
            active-class="palette-row--active"
            @click="run(entry)"
            @mousemove="select(sIdx, eIdx)"
          >
            <q-item-section avatar><q-icon :name="entry.icon" /></q-item-section>
            <q-item-section>
              <q-item-label>{{ entry.label }}</q-item-label>
              <q-item-label caption>{{ entry.caption }}</q-item-label>
            </q-item-section>
            <q-item-section side v-if="entry.badge"><q-badge outline :label="entry.badge" /></q-item-section>
          </q-item>
        </template>
      </q-list>
    </q-card>
  </q-dialog>
</template>
<script setup lang="ts">
// Palette v2 (Phase C3): Actions → Navigate → Graph, keyboard-complete
// (arrows move across sections, Enter executes, Esc closes).
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { surfaceModules } from '../design/ia'
import { graphSearch, kindIcons, routeForObject, type GraphSearchHit } from '../services/graph'

interface PaletteEntry {
  key: string
  label: string
  caption: string
  icon: string
  badge?: string
  action: () => void
}

const router = useRouter()
const open = ref(false)
const query = ref('')
const graphHits = ref<GraphSearchHit[]>([])
const graphLabel = ref('')
const cursor = ref<[number, number]>([0, 0])
let searchTimer: ReturnType<typeof setTimeout> | undefined

function navigate(path: string) {
  open.value = false
  query.value = ''
  graphHits.value = []
  cursor.value = [0, 0]
  void router.push(path)
}

// Actions execute a change, not just navigation; ?new=1 opens creation forms.
const ACTIONS: Omit<PaletteEntry, 'action'>[] = [
  { key: 'act-capture', label: 'Capture', caption: 'Quick capture — text, /task, /note, /secretary', icon: 'mdi-lightning-bolt-outline' },
  { key: 'act-new-task', label: 'New task', caption: 'Create a task in the inbox', icon: 'mdi-checkbox-marked-circle-auto-outline' },
  { key: 'act-new-project', label: 'New project', caption: 'Create a project', icon: 'mdi-folder-plus-outline' },
  { key: 'act-new-note', label: 'New note', caption: 'Create a Zettel', icon: 'mdi-note-plus-outline' },
  { key: 'act-open-day', label: 'Open / close the day', caption: 'Daily intention and review', icon: 'mdi-calendar-today' },
]
const ACTION_PATHS: Record<string, string> = {
  'act-capture': '/capture',
  'act-new-task': '/tasks?new=1',
  'act-new-project': '/projects?new=1',
  'act-new-note': '/zettelkasten',
  'act-open-day': '/today',
}

const filteredActions = computed<PaletteEntry[]>(() => {
  const q = query.value.toLowerCase().trim()
  return ACTIONS
    .filter((a) => !q || `${a.label} ${a.caption}`.toLowerCase().includes(q))
    .map((a) => ({ ...a, action: () => navigate(ACTION_PATHS[a.key]) }))
})

const filteredModules = computed<PaletteEntry[]>(() => {
  const q = query.value.toLowerCase().trim()
  return surfaceModules
    .filter((m) => !q || `${m.label} ${m.group} ${m.path}`.toLowerCase().includes(q))
    .map((m) => ({
      key: `nav-${m.id}`,
      label: m.label,
      caption: `${m.group} · ${m.path}`,
      icon: m.icon,
      action: () => navigate(m.path),
    }))
})

const graphEntries = computed<PaletteEntry[]>(() =>
  graphHits.value.map((hit) => ({
    key: `graph-${hit.object.id}`,
    label: hit.object.title || hit.object.kind,
    caption: `${hit.object.kind}${hit.object.status ? ` · ${hit.object.status}` : ''}${hit.snippet ? ` · ${hit.snippet.slice(0, 60)}` : ''}`,
    icon: kindIcons[hit.object.kind] ?? 'mdi-shape-outline',
    badge: hit.score.toFixed(2),
    action: () => navigate(routeForObject(hit.object)),
  })),
)

const sections = computed(() => [
  { title: 'Actions', entries: filteredActions.value },
  { title: 'Navigate', entries: filteredModules.value },
  { title: graphLabel.value ? `Graph · ${graphLabel.value}` : 'Graph', entries: graphEntries.value },
])

// --- keyboard cursor across sections ------------------------------------------
function flat(): [number, number][] {
  const coords: [number, number][] = []
  sections.value.forEach((section, s) => section.entries.forEach((_, e) => coords.push([s, e])))
  return coords
}
function isSelected(s: number, e: number): boolean {
  return cursor.value[0] === s && cursor.value[1] === e
}
function select(s: number, e: number) { cursor.value = [s, e] }
function move(delta: number) {
  const coords = flat()
  if (!coords.length) return
  const idx = coords.findIndex(([s, e]) => isSelected(s, e))
  const next = coords[(idx + delta + coords.length) % coords.length]
  cursor.value = next
}
function runSelected() {
  const [s, e] = cursor.value
  let entry = sections.value[s]?.entries[e]
  if (!entry) {
    const coords = flat()
    if (coords.length) entry = sections.value[coords[0][0]].entries[coords[0][1]]
  }
  if (entry) run(entry)
}
function run(entry: PaletteEntry) { entry.action() }

watch(query, (value) => {
  cursor.value = [0, 0]
  if (searchTimer) clearTimeout(searchTimer)
  const text = value.trim()
  if (text.length < 2) { graphHits.value = []; graphLabel.value = ''; return }
  searchTimer = setTimeout(async () => {
    try {
      const result = await graphSearch(text, [], 8)
      graphHits.value = result.hits
      // Honest search-mode label, e.g. "lexical search (no embedding model)".
      graphLabel.value = result.label
    } catch {
      graphHits.value = []
      graphLabel.value = ''
    }
  }, 220)
})

function onKeydown(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault(); open.value = true
  }
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
defineExpose({ open })
</script>
<style scoped lang="scss">
.palette-row--active {
  background: var(--nexus-text, #5dff86);
  color: var(--nexus-ink, #07130b);
  text-shadow: none;
}
</style>
