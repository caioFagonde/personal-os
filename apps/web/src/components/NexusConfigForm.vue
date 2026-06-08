<template>
  <q-form class="column q-gutter-md" @submit.prevent="submit">
    <q-input
      v-for="field in fields"
      :key="field.key"
      v-model="values[field.key]"
      outlined
      :label="field.label"
      :type="field.secret ? (visible[field.key] ? 'text' : 'password') : 'text'"
      :rules="[value => validate(field, value) || true]"
      autocomplete="off"
    >
      <template v-if="field.secret" #append>
        <q-btn flat round :icon="visible[field.key] ? 'mdi-eye-off' : 'mdi-eye'" @click="visible[field.key] = !visible[field.key]" />
      </template>
    </q-input>
    <q-banner class="bg-info text-white" rounded>
      Saved configuration is applied after the affected service is restarted. Secret values remain masked.
    </q-banner>
    <q-btn color="primary" type="submit" label="Validate and save" />
  </q-form>
</template>

<script setup lang="ts">
import { reactive } from 'vue'

export type ConfigField = {
  key: string
  label: string
  kind: 'url' | 'port' | 'phone' | 'whatsapp' | 'text'
  secret?: boolean
}

const props = defineProps<{ fields: ConfigField[]; initial?: Record<string, string> }>()
const emit = defineEmits<{ save: [values: Record<string, string>] }>()
const values = reactive<Record<string, string>>({ ...(props.initial || {}) })
const visible = reactive<Record<string, boolean>>({})

function validate(field: ConfigField, value: string): string | undefined {
  if (!value || value === '********') return
  if (field.kind === 'port' && (!/^\d+$/.test(value) || Number(value) < 1 || Number(value) > 65535)) return 'Use a port from 1 to 65535'
  if (field.kind === 'phone' && !/^\+[1-9]\d{7,14}$/.test(value)) return 'Use E.164 format, for example +15551234567'
  if (field.kind === 'whatsapp' && !/^whatsapp:\+[1-9]\d{7,14}$/.test(value)) return 'Use whatsapp:+<E.164 number>'
  if (field.kind === 'url') {
    try {
      const parsed = new URL(value)
      if (!['http:', 'https:'].includes(parsed.protocol)) return 'Use an absolute HTTP(S) URL'
    } catch { return 'Use an absolute HTTP(S) URL' }
  }
}

function submit() {
  const invalid = props.fields.some(field => validate(field, values[field.key] || ''))
  if (!invalid) emit('save', { ...values })
}
</script>
