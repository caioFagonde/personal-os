<template>
  <q-page class="column q-gutter-lg">
    <NexusPageHero eyebrow="1-click operational setup" title="Onboarding Wizard" subtitle="Run the bootstrap script, register this device, connect providers, test sync, subscribe to notifications, pair mobile, then create a backup." />

    <q-card class="glass-card">
      <q-card-section>
        <q-stepper v-model="step" vertical color="primary" animated flat>
          <q-step :name="1" title="Install core" icon="mdi-console" :done="step > 1">
            <p style="color:var(--nexus-muted)">Run the bootstrap script to start all core services and apply migrations.</p>
            <pre class="code-block">./scripts/bootstrap.sh --full</pre>
            <q-stepper-navigation><q-btn color="primary" label="Continue" @click="step = 2" /></q-stepper-navigation>
          </q-step>
          <q-step :name="2" title="Connect providers" icon="mdi-connection" :done="step > 2">
            <p style="color:var(--nexus-muted)">Open Connectors and authorize Google/Microsoft, test Twilio/ntfy, and verify Tailscale.</p>
            <q-btn to="/connectors" color="primary" label="Open connectors" class="q-mb-md" />
            <q-stepper-navigation><q-btn outline label="Continue" @click="step = 3" /></q-stepper-navigation>
          </q-step>
          <q-step :name="3" title="Pair devices" icon="mdi-cellphone-link" :done="step > 3">
            <p style="color:var(--nexus-muted)">Create a pairing code for your phone or tablet.</p>
            <q-btn to="/device-pairing" color="primary" label="Create pairing code" class="q-mb-md" />
            <q-stepper-navigation><q-btn outline label="Continue" @click="step = 4" /></q-stepper-navigation>
          </q-step>
          <q-step :name="4" title="Backup and restore drill" icon="mdi-backup-restore">
            <p style="color:var(--nexus-muted)">Create a backup, verify the archive, and confirm restore readiness.</p>
            <q-btn to="/backup-restore" color="primary" label="Open backup" />
          </q-step>
        </q-stepper>
      </q-card-section>
    </q-card>
  </q-page>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import NexusPageHero from '../components/NexusPageHero.vue'
const step = ref(1)
</script>
