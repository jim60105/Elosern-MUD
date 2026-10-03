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
});
const shown = computed(() => props.slots.slice(0, COMPANION_LINEUP_MAX));
const geometry = computed(() => companionSlots(shown.value.length));
const lineupStyle = computed(() => ({
  "--companion-count": shown.value.length,
  "--companion-exposure": -(geometry.value[1]?.x ?? 0),
}));
function slotStyle(index) {
  const { scale, lift, z } = geometry.value[index];
  const speaking = !shown.value[index].isControlled && shown.value[index].identity === props.speakingIdentity;
  return {
    height: `${scale * 100}%`, width: `${scale * 100}%`,
    right: `calc(${index} * var(--companion-step))`, bottom: `${lift * 100}%`, zIndex: speaking ? COMPANION_LINEUP_MAX + 1 : z,
  };
}
</script>

<template>
  <div class="companion-lineup" data-testid="companion-lineup" :style="lineupStyle" :data-count="shown.length" :data-compact="String(compact)" :data-motion-level="motionLevel" aria-hidden="true">
    <div
      v-for="(slot, index) in shown" :key="index"
      class="companion-lineup__slot" data-testid="companion-figure"
      :data-slot="index" :data-identity="slot.identity"
      :data-controlled="String(slot.isControlled)" :style="slotStyle(index)"
    >
      <StageActor
        :portrait="slot.portrait" :name="slot.displayName" side="left"
        :dimmed="slot.isControlled ? dimmed : slot.identity !== speakingIdentity" :motion-level="motionLevel"
        :gesture="slot.isControlled ? gesture : null"
        :gesture-key="slot.isControlled ? gestureKey : null"
        :float-amount="slot.isControlled ? floatAmount : null"
      />
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
.companion-lineup:not([data-count="1"]) {
  transform: translateX(max(0px, calc(var(--companion-reach) - var(--actor-left-inset) + 16px * var(--ui-scale))));
}
.companion-lineup[data-compact="true"]:not([data-count="1"]) {
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
@media (prefers-reduced-motion: reduce) { .companion-lineup__slot { transition: none; } }
/* In an overlapping row the rear glyph belongs in the exposed shoulder,
   not the occluded chest. Keep the shared fallback, with no invented art. */
.companion-lineup__slot:not([data-slot="0"]) .reference-artwork__chest {
  top: 32%;
  left: 0;
  right: auto;
  width: var(--companion-step);
}
.companion-lineup__slot:not([data-slot="0"]) .reference-artwork__placeholder-glyph {
  font-size: min(var(--text-2xl), var(--companion-step));
}
.companion-lineup__slot:not([data-slot="0"]) .reference-artwork__identity,
.companion-lineup__slot:not([data-slot="0"]) .reference-artwork__placeholder-label {
  display: none;
}
</style>
