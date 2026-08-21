<script setup>
// ChoicePointBlock (B2 action family): the narrative stream-end choice-point
// block. The stream is the AI-only surface — it renders `generating` and
// `ready` suggestions and nothing else — so the block derives its state from
// the committed `context_actions.suggestions` slice through the preserved
// choice-point reducer (lib/choicepoint.js, the same pure state machine the
// legacy adapter used): `generating` shows the muted line, `ready` shows the
// card row plus the shared dismiss control, and everything else mounts
// nothing.
//
// Movable: the block is a single stateless root element — the parent
// (the stream at C3) owns where it lives, so it can be re-parented as newer
// narrative text lands without re-creating or re-ordering its internals.
// The ready group also replaces the generating line in place (same root
// element across the transition), matching the legacy `replace` edge.
import { computed } from "vue";
import ChoicePointLogic from "../lib/choicepoint.js";
import ChoiceCardRow from "./ChoiceCardRow.vue";

const props = defineProps({
  // The committed `context_actions.suggestions` envelope
  // ({ status, cards }) or null (section absent).
  suggestions: { type: Object, default: null },
});

const emit = defineEmits(["action"]);

const state = computed(() =>
  ChoicePointLogic.nextChoicePointState(
    ChoicePointLogic.ABSENT,
    props.suggestions,
  ),
);

function dismiss() {
  // The same dismiss control belongs to the dock section and the narrative
  // choice-point group: `options.dismiss` with the exact empty payload.
  emit("action", { action_id: "options.dismiss", payload: {} });
}
</script>

<template>
  <div
    v-if="state !== ChoicePointLogic.ABSENT"
    class="choicepoint-block"
    :class="
      state === ChoicePointLogic.READY
        ? 'choicepoint-ready'
        : 'choicepoint-generating'
    "
    :data-state="state"
    data-testid="choicepoint-block"
  >
    <span v-if="state === ChoicePointLogic.GENERATING" class="choicepoint-generating__line">
      AI 正在構思建議…
    </span>
    <template v-else>
      <ChoiceCardRow
        :cards="(suggestions && suggestions.cards) || []"
        @action="(intent) => emit('action', intent)"
      />
      <button
        type="button"
        class="suggestions-dismiss"
        data-testid="choicepoint-dismiss"
        @click="dismiss"
      >✕ 清除建議</button>
    </template>
  </div>
</template>

<style scoped>
.choicepoint-block {
  box-sizing: border-box;
  margin: var(--sp-2) 0 var(--sp-3) 0;
  padding: var(--sp-3) var(--sp-4);
  background: var(--ink-860);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  font-family: var(--f-sans);
}

.choicepoint-generating__line {
  color: var(--paper-500);
  font-size: 0.9em;
}

.suggestions-dismiss {
  align-self: flex-end;
  padding: 2px var(--sp-2);
  color: var(--paper-300);
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  font-family: var(--f-sans);
  font-size: 0.8em;
  cursor: pointer;
}
</style>
