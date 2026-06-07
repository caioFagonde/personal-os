<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="Ops" title="Live Stack Certification" subtitle="Run browser tests against the actual Docker stack, certify mobile sync, and inspect release readiness." />

    <div class="module-grid">
      <q-card v-for="item in items" :key="item.title" class="glass-card">
        <q-card-section>
          <div class="row items-center q-gutter-sm q-mb-sm">
            <q-icon :name="item.icon" size="28px" />
            <div class="text-h6">{{ item.title }}</div>
          </div>
          <p style="color:var(--nexus-muted);font-size:13px">{{ item.body }}</p>
          <code class="code-block" style="display:block;font-size:12px">{{ item.command }}</code>
        </q-card-section>
      </q-card>
    </div>
  </q-page>
</template>
<script setup lang="ts">
import NexusPageHero from '../components/NexusPageHero.vue'

const items = [
  { icon: 'mdi-web', title: 'Live Playwright', body: 'Run UI flows against Docker services, not only static SPA.', command: 'make certify-live-stack' },
  { icon: 'mdi-cellphone-link', title: 'Physical Android sync', body: 'Deploy APK, adb reverse ports, create offline mutation, and verify sync health.', command: 'make certify-physical-sync' },
  { icon: 'mdi-brain', title: 'Model runtime', body: 'Certify OCR/object/audio runtime fallback and provider readiness.', command: 'make certify-model-runtime' },
  { icon: 'mdi-package-up', title: 'Publish release', body: 'Create signed artifacts and optionally publish a GitHub release.', command: 'make publish-release' },
]
</script>
