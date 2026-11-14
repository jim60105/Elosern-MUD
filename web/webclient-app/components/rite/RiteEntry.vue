<script setup>
// RiteEntry (landmark-rite-stage design D4; landmark rites design §12.2):
// the return entry under the place card while the committed `rite` panel is
// available and neither the rite card nor the stage is open. One button,
// `◆ <guardian> 儀式` with its key R; activating it emits `open` and the host
// reopens the arrival card as a revisit. It sends nothing.
import { ref } from "vue";

defineProps({
  // The guardian's name, from the committed `rite` panel.
  guardian: { type: String, required: true },
});
const emit = defineEmits(["open"]);

const button = ref(null);
function focus() {
  button.value?.focus({ preventScroll: true });
}
defineExpose({ focus });
</script>

<template>
  <button
    ref="button"
    type="button"
    class="rite-entry"
    data-testid="rite-entry"
    :aria-label="`${guardian} 儀式`"
    :title="`${guardian} 儀式 (R)`"
    @click="emit('open')"
  >
    <span class="rite-entry__gem" aria-hidden="true"></span>
    <span class="rite-entry__text"><b class="rite-entry__guardian">{{ guardian }}</b> 儀式</span>
    <kbd class="rite-entry__key" aria-hidden="true">R</kbd>
  </button>
</template>

<style>
/* The return entry: a quiet ink chip under the place card, right-aligned in
   the map column, with the gold gem the rite surfaces share. */
.rite-entry {
  flex: none;
  align-self: flex-end;
  box-sizing: border-box;
  max-width: 100%;
  display: inline-flex;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
  min-height: calc(40px * var(--ui-scale));
  padding: 0 calc(10px * var(--ui-scale)) 0 calc(14px * var(--ui-scale));
  border: 1px solid rgba(185, 154, 96, 0.5);
  border-radius: var(--radius-sm);
  background:
    linear-gradient(90deg, rgba(189, 164, 119, 0.12), transparent 70%),
    rgba(12, 13, 17, 0.86);
  backdrop-filter: blur(calc(9px * var(--ui-scale)));
  -webkit-backdrop-filter: blur(calc(9px * var(--ui-scale)));
  box-shadow: 0 calc(6px * var(--ui-scale)) calc(18px * var(--ui-scale)) rgba(0, 0, 0, 0.35);
  color: var(--paper-200);
  font: var(--text-md)/1 var(--f-sans);
  letter-spacing: 0.08em;
  cursor: pointer;
  pointer-events: auto;
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    background-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
}
.rite-entry__gem {
  flex: none;
  width: calc(7px * var(--ui-scale));
  height: calc(7px * var(--ui-scale));
  background: var(--gold-400);
  box-shadow: 0 0 calc(6px * var(--ui-scale)) rgba(228, 200, 142, 0.55);
  transform: rotate(45deg);
}
.rite-entry__text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rite-entry__guardian {
  color: var(--gold-300);
  font-family: var(--f-display);
  font-weight: 400;
  letter-spacing: 0.12em;
}
.rite-entry__key {
  flex: none;
  font: var(--text-xs)/1 var(--f-sans);
  color: var(--gold-300);
  padding: calc(3px * var(--ui-scale)) calc(6px * var(--ui-scale));
  border: 1px solid rgba(228, 200, 142, 0.35);
  border-radius: calc(3px * var(--ui-scale));
  background: rgba(228, 200, 142, 0.06);
}
.rite-entry:hover,
.rite-entry:focus-visible {
  border-color: var(--gold-400);
  background-color: var(--gold-glow);
  color: var(--paper-50);
  outline: none;
}
.rite-entry:focus-visible {
  box-shadow:
    0 0 0 1px var(--gold-400),
    0 calc(6px * var(--ui-scale)) calc(18px * var(--ui-scale)) rgba(0, 0, 0, 0.35);
}
</style>
