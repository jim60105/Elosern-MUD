<script setup>
// The rite panel (prototype): the new panel in the `choices` anchor of the
// AVG stage. It is the shared ChoiceCard (the dialogue choice list's frame
// and keyboard composite) under one chrome line that names the performer.
// Rows: one per ritual story (its digit and its label; a gold pip marks a
// story not yet experienced; the time cost is not shown), then 退開 under the hairline rule.
//
// The performer is picked on the stage, exactly as a combat target is: the
// figures are the hit areas, the picked one is lit and the others dim. This
// panel only states the result in text and offers the keyboard path
// (← / → step through the eligible figures). A story with no watch scene is
// disabled, with its reason, while a companion is the performer.
import { computed } from "vue";
import ChoiceCard from "../../../web/webclient-app/components/ChoiceCard.vue";

const props = defineProps({
  options: { type: Array, required: true },
  seen: { type: Array, default: () => [] },
  // {id, name, self}
  performer: { type: Object, required: true },
  // More than one eligible figure stands on the stage.
  canSwitch: { type: Boolean, default: false },
  entrance: { type: Boolean, default: true },
});
const emit = defineEmits(["perform", "leave", "step-performer"]);

const rows = computed(() => [
  ...props.options.map((option, index) => {
    const blocked = !props.performer.self && !option.watch;
    return {
      key: option.key,
      badge: String(index + 1),
      label: option.label,
      enabled: !blocked,
      reason: blocked ? "這個儀式只能親自進行" : null,
      unread: !blocked && !props.seen.includes(option.key),
    };
  }),
  { key: "leave", label: "退開", icon: "close", kind: "leave", back: true },
]);

function onKeydownCapture(event) {
  if (!props.canSwitch || event.ctrlKey || event.altKey || event.metaKey) return;
  if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
    event.preventDefault();
    event.stopPropagation();
    emit("step-performer", event.key === "ArrowLeft" ? -1 : 1);
  }
}
</script>

<template>
  <div class="rite-panel" @keydown.capture="onKeydownCapture">
    <p class="rite-panel__performer" aria-live="polite">
      <span class="rite-panel__performer-label">執行者</span>
      <span class="rite-panel__performer-name">{{ performer.name }}</span>
      <span v-if="canSwitch" class="rite-panel__performer-hint">點立繪或 <kbd>←</kbd><kbd>→</kbd> 換人</span>
    </p>
    <ChoiceCard
      :rows="rows"
      :view-key="`rite-${performer.id}`"
      :trailing-index="options.length"
      aria-label="儀式"
      test-id="rite-panel"
      :entrance="entrance"
      :digit-rows="options.length"
      trap-focus
      autofocus
      @pick="(key) => emit('perform', key)"
      @back="emit('leave')"
    />
  </div>
</template>

<style>
.rite-panel {
  position: relative;
  align-self: center;
  width: min(100%, calc(560px * var(--ui-scale)));
  pointer-events: auto;
}
/* The performer line sits inside the card frame, above its rows. */
.rite-panel > .choice-card {
  padding-top: calc(46px * var(--ui-scale));
}
.rite-panel__performer {
  position: absolute;
  z-index: 2;
  top: calc(12px * var(--ui-scale));
  left: calc(22px * var(--ui-scale));
  right: calc(22px * var(--ui-scale));
  display: flex;
  align-items: baseline;
  gap: calc(10px * var(--ui-scale));
  margin: 0;
  padding-bottom: calc(6px * var(--ui-scale));
  border-bottom: 1px solid rgba(185, 154, 96, 0.18);
  font: var(--text-sm)/1.5 var(--f-sans);
  white-space: nowrap;
  pointer-events: none;
}
.rite-panel__performer-label {
  color: var(--paper-500);
  letter-spacing: 0.2em;
}
.rite-panel__performer-name {
  color: var(--paper-50);
  font-weight: 600;
  letter-spacing: 0.08em;
}
.rite-panel__performer-hint {
  margin-left: auto;
  color: var(--paper-500);
  font-size: var(--text-xs);
}
.rite-panel__performer-hint kbd {
  margin: 0 calc(1px * var(--ui-scale));
  padding: 0 calc(4px * var(--ui-scale));
  border: 1px solid var(--ink-600);
  border-bottom-width: 2px;
  border-radius: var(--radius-sm);
  background: var(--ink-780);
  color: var(--paper-300);
  font-family: var(--f-mono);
}
</style>
