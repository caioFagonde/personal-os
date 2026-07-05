<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Ops" title="Ops Deck" subtitle="Certification, release, live-stack checks, and readiness — out of daily nav, one keypress away.">
      <template #actions>
        <q-btn outline icon="mdi-shield-sync-outline" label="Continuity" to="/continuity" />
      </template>
    </NexusPageHero>

    <div class="module-grid">
      <q-card v-for="surface in surfaces" :key="surface.path" class="glass-card">
        <q-card-section>
          <div class="row items-center q-gutter-sm">
            <q-icon :name="surface.icon" size="22px" />
            <div class="text-h6">{{ surface.label }}</div>
          </div>
          <p class="q-mt-sm text-caption" style="color:var(--nexus-muted)">{{ surface.blurb }}</p>
        </q-card-section>
        <q-card-actions>
          <q-btn flat color="primary" size="sm" :label="`Open ${surface.label}`" :to="surface.path" />
        </q-card-actions>
      </q-card>
    </div>
  </q-page>
</template>
<script setup lang="ts">
import NexusPageHero from '../components/NexusPageHero.vue'

const surfaces = [
  { label: 'Certification', path: '/certification', icon: 'mdi-certificate-outline', blurb: 'Run the v1 certification suite and inspect gate results.' },
  { label: 'Release Center', path: '/release-center', icon: 'mdi-rocket-launch-outline', blurb: 'Release manifests, signing pipeline, and channel state.' },
  { label: 'Live Stack', path: '/live-stack', icon: 'mdi-server-network', blurb: 'Runtime health of every composed service.' },
  { label: 'Initial Readiness', path: '/initial-readiness', icon: 'mdi-checkbox-multiple-marked-outline', blurb: 'The v1 north-star checklist, live-checked.' },
  { label: 'Model Runtime', path: '/model-runtime', icon: 'mdi-brain', blurb: 'OCR/vision/audio/embedding providers and their honest states.' },
]
</script>
