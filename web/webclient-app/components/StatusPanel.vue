<script setup>
// StatusPanel (H2, webclient-hud-02-status-islands, design D1): the
// `hud-left` island stack. It composes three separately-chromed islands —
// CharacterHead, VitalsTrack, and ConditionChips — replacing the single
// boxed column card H1 had re-homed here. The preserved
// `data-testid="status-panel"` root and the three
// `status-panel__gauge-value--{hp,mp,sp}` hooks (now carried by the
// VitalsTrack rows) keep the combat and transport-mount browser journeys
// unchanged.
import CharacterHead from "./CharacterHead.vue";
import ConditionChips from "./ConditionChips.vue";
import VitalsTrack from "./VitalsTrack.vue";

const props = defineProps({
  // The committed `status` v1 panel payload.
  status: { type: Object, required: true },
  // The committed `character` v3 panel payload.
  character: { type: Object, required: true },
  // The derived low-HP presentation state from the store's `view.vitals`
  // slice (design D5); forwarded to the vitals island.
  lowHp: { type: Boolean, default: false },
  // The committed transport revision and epoch: drive the vitals trailing
  // (ghost) bar's update rule (design D4) — the ghost keeps the previously
  // committed ratio within an epoch and resets on an epoch change.
  revision: { type: [Number, String], default: null },
  epoch: { type: [Number, String], default: null },
});
</script>

<template>
  <div class="island-stack" data-testid="status-panel">
    <CharacterHead :status="status" :character="character" />
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
   gap: 9px;
   /* The stack root is a transparent container; each child island carries
      the shared island chrome (design D2.1). The anchor's own 9px gap
      separates the islands. `min-height: 0` lets the whole stack compress
      inside the capped hud-left anchor instead of overflowing the budget. */
   min-height: 0;
   font-family: var(--f-sans);
 }
</style>
