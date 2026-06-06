<template>
  <q-dialog v-model="open" maximized transition-show="jump-down" transition-hide="jump-up">
    <q-card class="command-palette glass-panel">
      <q-card-section class="row items-center q-gutter-sm">
        <q-icon name="mdi-command" size="28px" />
        <q-input v-model="query" autofocus borderless placeholder="Search modules, actions, and workflows…" class="col" @keyup.enter="runFirst" />
        <q-btn flat round icon="mdi-close" @click="open = false" />
      </q-card-section>
      <q-separator />
      <q-list class="command-palette__results">
        <q-item v-for="item in filtered" :key="item.id" clickable @click="go(item.path)">
          <q-item-section avatar><q-icon :name="item.icon" /></q-item-section>
          <q-item-section>
            <q-item-label>{{ item.label }}</q-item-label>
            <q-item-label caption>{{ item.group }} · {{ item.path }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>
  </q-dialog>
</template>
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { navigationModules } from '../design/tokens'
const router = useRouter()
const open = ref(false)
const query = ref('')
const filtered = computed(() => {
  const q = query.value.toLowerCase().trim()
  if (!q) return navigationModules
  return navigationModules.filter((m) => `${m.label} ${m.group} ${m.path}`.toLowerCase().includes(q))
})
function go(path: string) { open.value = false; query.value = ''; router.push(path) }
function runFirst() { if (filtered.value[0]) go(filtered.value[0].path) }
function onKeydown(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault(); open.value = true
  }
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
defineExpose({ open })
</script>
