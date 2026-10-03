<script setup>
// StatusPanel: the lower-left vitals dock (vitals-bar-redesign design D4).
// One chromed surface standing on the band's top edge: the chromeless
// condition icon row (ConditionChips) over the three compact bars
// (VitalsTrack). The dock chrome lives on this root only; both children are
// transparent. The preserved `data-testid="status-panel"` root and the three
// `status-panel__gauge-value--{hp,mp,sp}` hooks (now the on-track numerals)
// keep the combat and transport-mount browser journeys unchanged.
//
// The reveal (webclient-scene-transitions, design D6): the `v-show` root sits
// inside a `<Transition>`, so the dock fades in while rising 12px out of the
// band's edge and sinks back into it when it hides. From the hiding commit on it is
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
      <ConditionChips :conditions="status.conditions || []" :revealed="visible" />
      <VitalsTrack
        :status="status"
        :low-hp="lowHp"
        :revision="revision"
        :epoch="epoch"
        :display-hp="displayHp"
      />
    </div>
  </Transition>
</template>

<style scoped>
/* The dock (vitals-bar-redesign design D4): not a box but a mounted
   instrument. Its ground is a smoke of the shared panel ink that is densest
   at the brass spine and thins out to the right and towards the top, so the
   art reads through its far edge; the backdrop blur thins with it. A brass
   lozenge — the band's own ornament — caps a hairline spine that runs down
   the dock's left side towards the band, and a hairline crown runs from it
   along the top, fading out before the right end. The content stands to the
   right of the spine; both children stay transparent. */
.island-stack {
  position: relative;
  isolation: isolate;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: calc(6px * var(--ui-scale));
  min-width: 0;
  width: 100%;
  padding: calc(15px * var(--ui-scale)) calc(18px * var(--ui-scale)) calc(10px * var(--ui-scale)) calc(26px * var(--ui-scale));
  color: var(--paper-100);
  overflow-wrap: anywhere;
  /* `min-height: 0` lets the dock compress inside the capped vitals anchor
     instead of overflowing the budget. */
  min-height: 0;
  font-family: var(--f-sans);
}
.island-stack::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  background: var(--panel);
  backdrop-filter: blur(calc(9px * var(--ui-scale)));
  -webkit-backdrop-filter: blur(calc(9px * var(--ui-scale)));
  -webkit-mask-image:
    linear-gradient(90deg, #000 0%, #000 52%, rgba(0, 0, 0, 0.55) 78%, transparent 100%),
    linear-gradient(0deg, #000 0%, #000 62%, transparent 100%);
  -webkit-mask-composite: source-in;
  mask-image:
    linear-gradient(90deg, #000 0%, #000 52%, rgba(0, 0, 0, 0.55) 78%, transparent 100%),
    linear-gradient(0deg, #000 0%, #000 62%, transparent 100%);
  mask-composite: intersect;
  pointer-events: none;
}
.island-stack::after {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  background:
    var(--band-ornament) 0 0 / calc(30px * var(--ui-scale)) calc(11px * var(--ui-scale)) no-repeat,
    linear-gradient(90deg, var(--band-edge), var(--band-edge-dim) 45%, transparent)
      calc(30px * var(--ui-scale)) calc(5px * var(--ui-scale)) / calc(72% - 30px * var(--ui-scale)) 1px no-repeat,
    linear-gradient(180deg, var(--band-edge), var(--band-edge-dim) 55%, transparent)
      calc(15px * var(--ui-scale)) calc(11px * var(--ui-scale)) / 1px calc(100% - 11px * var(--ui-scale)) no-repeat;
  pointer-events: none;
}

/* The reveal (webclient-scene-transitions, design D6; vitals-bar-redesign
   task 1.5): the bottom-anchored dock rises 12px out of the band's edge as
   it fades in, and sinks 12px back toward the band as it fades out — the
   enter/exit easing curves, never an overshoot. Without travel (the reduced
   level) it only fades. */
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
  transform: translateY(calc(var(--motion-shift-sm) * var(--motion-travel)));
}
</style>
