<template>
  <q-page class="q-pa-md column q-gutter-md">
    <section class="glass-panel q-pa-lg row items-center justify-between q-gutter-md">
      <div>
        <div class="text-h4">Task Inbox</div>
        <p class="text-subtitle2 text-grey-4">Inbox, delegated work, waiting loops, follow-ups, and completion tracking.</p>
      </div>
      <q-btn color="primary" icon="mdi-refresh" label="Refresh" @click="load" />
    </section>
    <q-list bordered separator class="glass-panel">
      <q-item v-for="task in tasks" :key="task.id">
        <q-item-section avatar><q-icon :name="task.status === 'delegated' ? 'mdi-account-arrow-right' : 'mdi-checkbox-blank-circle-outline'" /></q-item-section>
        <q-item-section>
          <q-item-label>{{ task.title }}</q-item-label>
          <q-item-label caption>{{ task.status }} · p{{ task.priority }} · {{ task.assignee_key || 'self' }}</q-item-label>
        </q-item-section>
        <q-item-section side>
          <q-btn flat round icon="mdi-check" @click="complete(task.id)" />
        </q-item-section>
      </q-item>
    </q-list>
  </q-page>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { captureUrl, jsonFetch } from '../services/api'
const tasks = ref<any[]>([])
async function load() { tasks.value = await jsonFetch(`${captureUrl}/api/tasks`) }
async function complete(id: string) { await jsonFetch(`${captureUrl}/api/tasks/${id}`, { method: 'PATCH', body: JSON.stringify({ status: 'completed' }) }); await load() }
onMounted(load)
</script>
