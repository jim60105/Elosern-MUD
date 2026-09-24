<script setup>
// StatusPanel: the `vitals` anchor's island stack. It composes two separately-chromed
// islands — VitalsTrack and ConditionChips. The preserved
// `data-testid="status-panel"` root and the three
// `status-panel__gauge-value--{hp,mp,sp}` hooks (carried by the VitalsTrack
// rows) keep the combat and transport-mount browser journeys unchanged.
import ConditionChips from "./ConditionChips.vue";
import VitalsTrack from "./VitalsTrack.vue";

const props = defineProps({
  // The committed `status` v1 panel payload.
  status: { type: Object, required: true },
  // The derived low-HP presentation state from the store's `view.vitals`
  // slice (design D5); forwarded to the vitals island.
  lowHp: { type: Boolean, default: false },
  // The committed transport revision and epoch: drive the vitals trailing
  // (ghost) bar's update rule (design D4) — the ghost keeps the previously
  // committed ratio within an epoch and resets on an epoch change.
  revision: { type: [Number, String], default: null },
  epoch: { type: [Number, String], default: null },
  // Vitals island visibility derived client-side (design D1/D2). Hidden
  // with v-show (display: none) at full health outside combat while keeping
  // VitalsTrack mounted so trailing bar memory is preserved.
  visible: { type: Boolean, default: true },
});
</script>

<template>
  <div v-show="visible" class="island-stack" data-testid="status-panel">
    <VitalsTrack
      :status="status"
      :low-hp="lowHp"
      :revision="revision"
      :epoch="epoch"
    />
    <ConditionChips :conditions="status.conditions || []" />
  </div>
</template>

<style scoped>
/* The stack root is a transparent container; each child island carries
   the shared island chrome (design D2.1). The anchor's own 9px gap
   separates the islands. */
.island-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  width: 100%;
  color: var(--paper-100);
  overflow-wrap: anywhere;
  /* The stack root is a transparent container; each child island carries
     the shared island chrome (design D2.1). The anchor's own 9px gap
     separates the islands. `min-height: 0` lets the whole stack compress
     inside the capped vitals anchor instead of overflowing the budget. */
  min-height: 0;
  font-family: var(--f-sans);
}
</style>
