<script setup>
import { computed } from "vue";
import StageActor from "./StageActor.vue";
import { companionSlots, COMPANION_LINEUP_MAX } from "./companion-lineup.js";

const props = defineProps({
  slots: { type: Array, default: () => [] },
  dimmed: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
  speakingIdentity: { type: Number, default: null },
  motionLevel: { type: String, default: "full" },
  gesture: { type: String, default: null },
  gestureKey: { type: String, default: null },
  floatAmount: { type: Number, default: null },
  // The engine's party side in combat (`formation.party`: `{ figures:
  // [{ box, z }] }`, stage pixels; webclient-combat-formation D1/D3), or null
  // outside combat, where the overlapping exploration row below applies
  // unchanged.
  formation: { type: Object, default: null },
  // Whether a re-formed line glides (false on a resize, a reconnect, and
  // below `full`).
  glide: { type: Boolean, default: true },
});
const shown = computed(() => props.slots.slice(0, COMPANION_LINEUP_MAX));
const geometry = computed(() => companionSlots(shown.value.length));
const lineupStyle = computed(() => ({
  "--companion-count": shown.value.length,
  "--companion-exposure": -(geometry.value[1]?.x ?? 0),
}));
function slotStyle(index) {
  const figure = props.formation?.figures?.[index];
  if (figure) {
    const { left, top, width, height } = figure.box;
    return { left: `${left}px`, top: `${top}px`, width: `${width}px`, height: `${height}px`, zIndex: figure.z };
  }
  const { scale, lift, z } = geometry.value[index];
  const speaking = !shown.value[index].isControlled && shown.value[index].identity === props.speakingIdentity;
  return {
    height: `${scale * 100}%`, width: `${scale * 100}%`,
    right: `calc(${index} * var(--companion-step))`, bottom: `${lift * 100}%`, zIndex: speaking ? COMPANION_LINEUP_MAX + 1 : z,
  };
}
</script>

<template>
  <div
    class="companion-lineup" data-testid="companion-lineup" :style="lineupStyle" :data-count="shown.length"
    :data-compact="String(compact)" :data-motion-level="motionLevel"
    :data-formation="formation ? 'true' : null" :data-glide="glide ? 'true' : 'false'" aria-hidden="true"
  >
    <div
      v-for="(slot, index) in shown" :key="index"
      class="companion-lineup__slot" data-testid="companion-figure"
      :data-slot="index" :data-identity="slot.identity"
      :data-controlled="String(slot.isControlled)" :data-rank="formation?.figures?.[index]?.rank ?? null" :style="slotStyle(index)"
    >
      <div class="formation-figure" :data-glide-key="`party:${slot.identity ?? `slot-${index}`}`">
      <StageActor
        :artwork="slot.artwork" :panel="slot.panel" :has-reference="slot.hasReference"
        :name="slot.displayName" side="left"
        :dimmed="slot.isControlled ? dimmed : slot.identity !== speakingIdentity" :motion-level="motionLevel"
        :gesture="slot.isControlled ? gesture : null"
        :gesture-key="slot.isControlled ? gestureKey : null"
        :float-amount="slot.isControlled ? floatAmount : null"
      />
      </div>
    </div>
  </div>
</template>

<style>
.companion-lineup {
  --companion-count: 1;
  --companion-exposure: 0;
  --companion-step: calc(var(--companion-exposure) * var(--actor-h) * 2 / 3);
  --companion-reach: calc((var(--companion-count) - 1) * var(--companion-step));
  position: relative; height: 100%; width: 100%; pointer-events: none;
}
.companion-lineup:not([data-count="1"]):not([data-formation="true"]) {
  transform: translateX(max(0px, calc(var(--companion-reach) - var(--actor-left-inset) + 16px * var(--ui-scale))));
}
.companion-lineup[data-compact="true"]:not([data-count="1"]):not([data-formation="true"]) {
  --companion-step: clamp(0px, calc((max(30vw, 50vw - 280px * var(--ui-scale)) - 32px * var(--ui-scale) - var(--actor-h) * 2 / 3) / (var(--companion-count) - 1)), calc(var(--companion-exposure) * var(--actor-h) * 2 / 3));
  transform: translateX(calc(var(--companion-reach) - var(--actor-left-inset) + 16px * var(--ui-scale)));
}
.companion-lineup__slot {
  position: absolute;
  transition: height var(--motion-portrait) var(--ease-standard), width var(--motion-portrait) var(--ease-standard),
    right var(--motion-portrait) var(--ease-standard), bottom var(--motion-portrait) var(--ease-standard);
  pointer-events: none;
}
.companion-lineup[data-motion-level="off"] .companion-lineup__slot { transition: none; }
.companion-lineup__slot > .formation-figure { position: relative; height: 100%; }
.companion-lineup__slot > .formation-figure > .stage-actor { height: 100%; }
/* Combat (webclient-combat-formation D1/D3): the anchor spans the stage and
   each slot stands at its formation box in stage pixels; the exploration
   row's sideways shift is off. A re-formed line glides every box on the
   travel duration and easing the foes' slots share, so both sides change
   size together; on a resize, a reconnect and below `full` it is instant. */
.companion-lineup[data-formation="true"] {
  position: absolute;
  inset: 0;
  transform: none;
}
.companion-lineup[data-formation="true"] > .companion-lineup__slot {
  transition:
    left calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard),
    top calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard),
    width calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard),
    height calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard);
}
.companion-lineup[data-formation="true"][data-glide="false"] > .companion-lineup__slot { transition: none; }
/* The placeholder at the formation's scale (the foes' own rule); the
   rear figures' labels leave where the figures overlap, as the foes' do —
   each companion's plate names it. */
.companion-lineup[data-formation="true"]:not([data-count="1"]) > .companion-lineup__slot:not([data-slot="0"]) .reference-artwork__identity,
.companion-lineup[data-formation="true"]:not([data-count="1"]) > .companion-lineup__slot:not([data-slot="0"]) .reference-artwork__placeholder-label {
  display: none;
}
.companion-lineup[data-formation="true"] .reference-artwork__placeholder-glyph {
  width: calc(clamp(88px * var(--ui-scale), 11vh, 132px * var(--ui-scale)) * var(--formation-scale, 1));
  font-size: calc(clamp(44px * var(--ui-scale), 5.6vh, 66px * var(--ui-scale)) * var(--formation-scale, 1));
}
@media (prefers-reduced-motion: reduce) { .companion-lineup__slot { transition: none; } }
/* In an overlapping row the rear glyph belongs in the exposed shoulder,
   not the occluded chest. Keep the shared fallback, with no invented art. */
.companion-lineup:not([data-formation="true"]) > .companion-lineup__slot:not([data-slot="0"]) .reference-artwork__chest {
  top: 32%;
  left: 0;
  right: auto;
  width: var(--companion-step);
}
.companion-lineup:not([data-formation="true"]) > .companion-lineup__slot:not([data-slot="0"]) .reference-artwork__placeholder-glyph {
  font-size: min(var(--text-2xl), var(--companion-step));
}
.companion-lineup:not([data-formation="true"]) > .companion-lineup__slot:not([data-slot="0"]) .reference-artwork__identity,
.companion-lineup:not([data-formation="true"]) > .companion-lineup__slot:not([data-slot="0"]) .reference-artwork__placeholder-label {
  display: none;
}
</style>
