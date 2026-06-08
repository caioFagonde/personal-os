<template>
  <q-card class="glass-card provider-card">
    <q-card-section>
      <div class="row items-start no-wrap q-gutter-sm q-mb-sm">
        <q-avatar rounded :color="stateDisplay.color" text-color="white" :icon="manifest.icon" size="42px" />
        <div class="col">
          <div class="row items-center no-wrap q-gutter-xs">
            <div class="text-h6" style="line-height:1.2">{{ manifest.name }}</div>
            <q-badge :color="stateDisplay.color" :label="stateDisplay.label" />
          </div>
          <div class="text-caption" style="color:var(--nexus-muted)">{{ categoryLabel }}</div>
        </div>
      </div>

      <p class="provider-desc">{{ manifest.description }}</p>

      <div class="row q-gutter-xs q-mb-sm" style="flex-wrap:wrap">
        <q-badge
          v-for="tag in manifest.costTags"
          :key="tag"
          :color="costDisplay(tag).color"
          :label="costDisplay(tag).label"
          outline
          class="provider-cost-badge"
        />
      </div>

      <div v-if="manifest.capabilities.length" class="provider-caps q-mb-sm">
        <q-chip
          v-for="cap in manifest.capabilities"
          :key="cap"
          :label="cap"
          dense
          size="sm"
          outline
        />
      </div>

      <q-banner
        v-if="manifest.cloudSafetyNote"
        class="cloud-safety-banner q-mb-sm"
        rounded
        dense
      >
        <template #avatar><q-icon name="mdi-shield-alert-outline" color="warning" /></template>
        <span class="text-caption">{{ manifest.cloudSafetyNote }}</span>
      </q-banner>

      <q-expansion-item
        v-if="status.state === 'needs_config' || status.state === 'not_installed' || status.state === 'malformed_config'"
        icon="mdi-cog-outline"
        label="Configuration"
        header-class="text-accent"
        dense
      >
        <div class="q-pa-sm">
          <div class="text-caption q-mb-sm" style="color:var(--nexus-muted)">
            Add the following to your <code>.env</code> and restart the relevant service:
          </div>
          <div v-for="req in manifest.envRequirements" :key="req.key" class="env-req-row">
            <code>{{ req.key }}</code>
            <span class="text-caption" style="color:var(--nexus-muted)"> &mdash; {{ req.label }}</span>
            <q-badge v-if="req.secret" color="warning" label="secret" dense class="q-ml-xs" />
          </div>
        </div>
      </q-expansion-item>

      <div v-if="status.message" class="text-caption q-mt-sm" style="color:var(--nexus-muted)">
        {{ status.message }}
      </div>
    </q-card-section>

    <q-card-actions align="right">
      <slot name="actions" :status="status" :manifest="manifest" />
    </q-card-actions>
  </q-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  type ProviderManifest,
  type ProviderLiveStatus,
  type CostTag,
  STATE_DISPLAY,
  COST_DISPLAY,
  PROVIDER_CATEGORIES,
} from '../providers/manifests'

const props = defineProps<{
  manifest: ProviderManifest
  status: ProviderLiveStatus
}>()

const stateDisplay = computed(() => STATE_DISPLAY[props.status.state])
const categoryLabel = computed(() => PROVIDER_CATEGORIES[props.manifest.category].label)

function costDisplay(tag: CostTag) {
  return COST_DISPLAY[tag]
}
</script>

<style scoped>
.provider-card {
  min-height: 200px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.provider-desc {
  color: var(--nexus-muted);
  font-size: 13px;
  margin: 0 0 8px;
  line-height: 1.5;
}
.provider-caps {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.provider-cost-badge {
  font-size: 10px;
}
.env-req-row {
  padding: 4px 0;
  font-size: 13px;
}
.env-req-row code {
  background: rgba(0,0,0,0.22);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}
.cloud-safety-banner {
  background: rgba(255, 152, 0, 0.08) !important;
  border: 1px solid rgba(255, 152, 0, 0.2);
  font-size: 12px;
}
</style>
