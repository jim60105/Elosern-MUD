<script setup>
// OptionCard (B2 action family): one `context_actions` v5 suggestion card —
// the exact server-authored shape (`kind`, `action_code`, `label`, `params`,
// optional `hint`) rendered as text nodes (no card content ever enters a
// markup pipeline). Activation emits the exact OOB action intent (the
// `ui_action` envelope's `action_id` + `payload`) with no invented value:
// a `known_action` card carries its server-normalized `params` unchanged;
// a `freeform` card is `explore.talk_freeform` whose `speech` is always the
// label text (webclient-options-surface contract). The one card renderer is
// shared by the dock section and the narrative choice-point, so size,
// labels, and click paths cannot diverge.
import { computed } from "vue";

const props = defineProps({
  card: { type: Object, required: true },
});

const emit = defineEmits(["action"]);

const isFreeform = computed(() => props.card.kind === "freeform");
const hasHint = computed(
  () => typeof props.card.hint === "string" && props.card.hint.length > 0,
);

function activate() {
  const { card } = props;
  const intent = isFreeform.value
    ? {
        action_id: "explore.talk_freeform",
        payload: { npc_id: card.params.npc_id, speech: card.label },
      }
    : { action_id: card.action_code, payload: { ...card.params } };
  emit("action", intent);
}
</script>

<template>
  <button
    type="button"
    class="option-card"
    :class="isFreeform ? 'option-card-freeform' : 'option-card-known'"
    data-testid="option-card"
    @click="activate"
  >
    <span class="option-card-label">{{ card.label }}</span>
    <span v-if="hasHint" class="option-card-hint">{{ card.hint }}</span>
  </button>
</template>

<style scoped>
.option-card {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--sp-1);
  box-sizing: border-box;
  max-width: 16rem;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-100);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  line-height: 1.5;
  text-align: left;
  cursor: pointer;
}

.option-card-known {
  border-left: 3px solid var(--seal-500);
}

.option-card-freeform {
  border-left: 3px solid var(--gold-500);
}

.option-card-label {
  color: var(--paper-50);
}

.option-card-hint {
  color: var(--paper-500);
  font-size: 0.85em;
}
</style>
