<template>
  <q-page class="q-pa-md column q-gutter-md">
    <section class="glass-panel q-pa-lg">
      <div class="text-h4">Fast Capture</div>
      <p class="text-subtitle2 text-grey-4">Write once. The system creates a task, stores the note trail, and delegates when rules match.</p>
      <q-input v-model="text" type="textarea" autogrow filled label="Capture command or note" placeholder="/secretary whatsapp email due today 17h Ask João for the signed contract" />
      <div class="row q-gutter-sm q-mt-md">
        <q-btn color="primary" icon="mdi-lightning-bolt" label="Capture" @click="capture" :loading="loading" />
        <q-btn flat icon="mdi-account-tie" label="Secretary template" @click="text = '/secretary whatsapp email due today 17h '" />
      </div>
    </section>

    <section v-if="result" class="glass-panel q-pa-lg">
      <div class="text-h6">Created</div>
      <q-markup-table flat bordered>
        <tbody>
          <tr><td>Task</td><td>{{ result.task?.title }}</td></tr>
          <tr><td>Status</td><td>{{ result.task?.status }}</td></tr>
          <tr><td>Messages</td><td>{{ result.messages?.length || 0 }}</td></tr>
        </tbody>
      </q-markup-table>
      <q-list bordered separator class="q-mt-md" v-if="result.messages?.length">
        <q-item v-for="message in result.messages" :key="message.id">
          <q-item-section avatar><q-icon :name="message.channel === 'whatsapp' ? 'mdi-whatsapp' : 'mdi-email-outline'" /></q-item-section>
          <q-item-section>
            <q-item-label>{{ message.channel }} → {{ message.recipient }}</q-item-label>
            <q-item-label caption>{{ message.status }} · {{ message.connector }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </section>
  </q-page>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { captureUrl, jsonFetch } from '../services/api'
const text = ref('/secretary whatsapp email due today 17h Reschedule dentist appointment and ask João for the signed contract PDF.')
const result = ref<any>(null)
const loading = ref(false)
async function capture() {
  loading.value = true
  try {
    result.value = await jsonFetch(`${captureUrl}/api/capture`, { method: 'POST', body: JSON.stringify({ text: text.value, source_kind: 'quick_capture' }) })
  } finally { loading.value = false }
}
</script>
