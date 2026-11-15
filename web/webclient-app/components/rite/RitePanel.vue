<script setup>
// RitePanel (landmark-rite-surfaces design D4; landmark rites design §12.2):
// the rite panel in the `choices` anchor of the rite stage. It is the shared
// ChoiceCard: one digit row per option (a gold pip, named in text, marks an
// option not yet experienced), then 退開 under the hairline rule, with a
// header line inside the frame naming the performer it is given. While a
// companion performs, an option that does not admit a companion is disabled
// with its reason. It sends nothing: an activation emits `perform(key)` and
// 退開 or Escape emits `leave`.
//
// The performer is picked on the stage figures, as a combat target is
// (landmark-rite-performer-picking D4). While picking is offered
// (`canSwitch`) the header adds the switching hint and ArrowLeft /
// ArrowRight emit `step-performer(-1 | 1)`, caught in the capture phase so
// they never reach the card's own keys; otherwise the keys pass through.
import { computed, ref } from "vue";
import ChoiceCard from "../ChoiceCard.vue";
import { UNSEEN_LABEL, riteRows } from "./rite-model.js";

const props = defineProps({
  // The committed `rite` panel.
  rite: { type: Object, required: true },
  // One row of ritePerformers(rite).
  performer: { type: Object, required: true },
  entrance: { type: Boolean, default: true },
  // More than one listed performer, and an option a companion may perform.
  canSwitch: { type: Boolean, default: false },
});
const emit = defineEmits(["perform", "leave", "step-performer"]);

function onKeydownCapture(event) {
  if (!props.canSwitch || event.ctrlKey || event.altKey || event.metaKey || event.isComposing) return;
  if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
  event.preventDefault();
  event.stopPropagation();
  emit("step-performer", event.key === "ArrowLeft" ? -1 : 1);
}

const rows = computed(() => riteRows(props.rite, props.performer));

function onPick(key) {
  if (key === "leave") emit("leave");
  else emit("perform", key);
}

// The host hands focus back to the card's list (the rite stage re-takes it
// from the message page once the shell has presented the stage).
const card = ref(null);
function focus() {
  card.value?.focus();
}
defineExpose({ focus });
</script>

<template>
  <div class="rite-panel" @keydown.capture="onKeydownCapture">
    <ChoiceCard
      ref="card"
      :rows="rows"
      :view-key="`rite-${performer.id}`"
      :trailing-index="rite.options.length"
      :digit-rows="rite.options.length"
      :unread-label="UNSEEN_LABEL"
      aria-label="儀式"
      test-id="rite-panel"
      :entrance="entrance"
      trap-focus
      autofocus
      @pick="onPick"
      @back="emit('leave')"
    >
      <template #header>
        <p class="rite-panel__performer" aria-live="polite" data-testid="rite-panel-performer">
          <span class="rite-panel__performer-label">執行者</span>
          <span :key="performer.id" class="rite-panel__performer-name">{{ performer.name }}</span>
          <span v-if="canSwitch" class="rite-panel__performer-hint" data-testid="rite-panel-performer-hint">
            點立繪或 <kbd>←</kbd><kbd>→</kbd> 換人
          </span>
        </p>
      </template>
    </ChoiceCard>
  </div>
</template>

<style>
.rite-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  align-self: center;
  width: min(100%, calc(560px * var(--ui-scale)));
  max-height: 100%;
  min-height: 0;
  pointer-events: auto;
}
.rite-panel__performer {
  display: flex;
  align-items: baseline;
  gap: calc(10px * var(--ui-scale));
  margin: 0;
  font: var(--text-sm)/1.5 var(--f-sans);
  white-space: nowrap;
}
.rite-panel__performer-label {
  color: var(--paper-500);
  letter-spacing: 0.2em;
}
.rite-panel__performer-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--paper-50);
  font-weight: 600;
  letter-spacing: 0.08em;
}
/* A new performer's name settles in the way the rows do; the motion tokens
   resolve to 0 at the off level. */
.rite-panel__performer-name {
  animation: rite-panel-name-in var(--motion-reveal) var(--ease-enter) backwards;
}
@keyframes rite-panel-name-in {
  from {
    opacity: 0;
    transform: translateY(calc(var(--motion-shift-sm) * 0.5 * var(--motion-travel)));
  }
}
/* The switching hint: quiet text with keycap chips at the line's far end. */
.rite-panel__performer-hint {
  display: inline-flex;
  flex: none;
  align-items: baseline;
  gap: calc(3px * var(--ui-scale));
  margin-left: auto;
  color: var(--paper-500);
  font-size: var(--text-xs);
  letter-spacing: 0.06em;
}
.rite-panel__performer-hint kbd {
  min-width: calc(18px * var(--ui-scale));
  padding: 0 calc(4px * var(--ui-scale));
  border: 1px solid var(--ink-600);
  border-bottom-width: 2px;
  border-radius: var(--radius-sm);
  background: var(--ink-780);
  color: var(--paper-300);
  font-family: var(--f-mono);
  line-height: 1.35;
  text-align: center;
}
</style>
