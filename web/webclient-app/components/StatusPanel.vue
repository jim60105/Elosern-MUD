<script setup>
// StatusPanel: the `vitals` anchor's island stack. It composes two separately-chromed
// islands — VitalsTrack and ConditionChips. The preserved
// `data-testid="status-panel"` root and the three
// `status-panel__gauge-value--{hp,mp,sp}` hooks (carried by the VitalsTrack
// rows) keep the combat and transport-mount browser journeys unchanged.
//
// The reveal (webclient-scene-transitions, design D6): the `v-show` root sits
// inside a `<Transition>`, so the island fades and slides 12px into place
// when it shows and back out when it hides. From the hiding commit on it is
// inert (the shell's pre-flush rescue has already moved focus out), and it
// reaches `display: none` when its exit ends; shown again mid-exit, it is in
// reach again at once.
import { computed } from "vue";
import ConditionChips from "./ConditionChips.vue";
import VitalsTrack from "./VitalsTrack.vue";
import { inertWhileLeaving } from "../lib/transition_hooks.js";

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
  // The EFFECTIVE motion level (`store.view.motionLevel`,
  // webclient-scene-transitions D1): at `off` the transition has no CSS
  // phase, so the final state is on screen in the commit's frame (a CSS
  // phase would outlive the commit by a double frame even at 0s).
  motionLevel: { type: String, default: "full" },
  // The hit points a playing combat round displays (webclient-combat-beat-
  // queue D7), forwarded to the vitals island; null when nothing plays.
  displayHp: { type: Number, default: null },
});

const transitionCss = computed(() => props.motionLevel !== "off");
</script>

<template>
  <Transition name="vitals-reveal" :css="transitionCss" v-bind="inertWhileLeaving">
    <div v-show="visible" class="island-stack" data-testid="status-panel">
      <VitalsTrack
        :status="status"
        :low-hp="lowHp"
        :revision="revision"
        :epoch="epoch"
        :display-hp="displayHp"
      />
      <ConditionChips :conditions="status.conditions || []" />
    </div>
  </Transition>
</template>

<style scoped>
/* The stack root is a transparent container; each child island carries
   the shared island chrome (design D2.1). The anchor's own 9px gap
   separates the islands. */
.island-stack {
  display: flex;
  flex-direction: column;
  gap: calc(12px * var(--ui-scale));
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

/* The reveal (webclient-scene-transitions, design D6): the island drops
   12px into place under the place card as it fades in, and lifts back as it
   fades out. Without travel (the reduced level) it only fades. */
.vitals-reveal-enter-active {
  transition:
    opacity var(--motion-reveal) var(--ease-enter),
    transform var(--motion-reveal) var(--ease-enter);
}
.vitals-reveal-leave-active {
  transition:
    opacity var(--motion-reveal) var(--ease-exit),
    transform var(--motion-reveal) var(--ease-exit);
}
.vitals-reveal-enter-from,
.vitals-reveal-leave-to {
  opacity: 0;
  transform: translateY(calc(-1 * var(--motion-shift-sm) * var(--motion-travel)));
}
</style>
