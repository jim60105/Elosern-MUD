<script setup>
// RitePanel (landmark-rite-surfaces design D4; landmark rites design §12.2):
// the rite panel in the `choices` anchor of the rite stage. It is the shared
// ChoiceCard: one digit row per option (a gold pip, named in text, marks an
// option not yet experienced), then 退開 under the hairline rule, with a
// header line inside the frame naming the performer it is given. While a
// companion performs, an option that does not admit a companion is disabled
// with its reason. It sends nothing: an activation emits `perform(key)` and
// 退開 or Escape emits `leave`.
import { computed, ref } from "vue";
import ChoiceCard from "../ChoiceCard.vue";
import { UNSEEN_LABEL, riteRows } from "./rite-model.js";

const props = defineProps({
  // The committed `rite` panel.
  rite: { type: Object, required: true },
  // One row of ritePerformers(rite).
  performer: { type: Object, required: true },
  entrance: { type: Boolean, default: true },
});
const emit = defineEmits(["perform", "leave"]);

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
  <div class="rite-panel">
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
          <span class="rite-panel__performer-name">{{ performer.name }}</span>
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
</style>
