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
  // H3 (task 5.7): the row-mode identity. When `rowMode` is set, the card
  // renders `role="option"` with the `data-item-key` row identity so a card
  // can be a listbox option inside the suggestions pane. The narrative
  // choice-point keeps the plain-button usage (no `rowMode`).
  id: { type: String, default: null },
  itemKey: { type: String, default: null },
  rowMode: { type: Boolean, default: false },
  focused: { type: Boolean, default: false },
});

const emit = defineEmits(["action", "focus", "activate"]);

// H3: the card may arrive as the raw server shape (`kind`, `action_code`)
// or the store's normalized item shape (`action_id`, `params`). Both resolve
// to the same OOB intent.
const isFreeform = computed(() => {
  const c = props.card;
  if (c.kind === "freeform") {
    return true;
  }
  return c.kind === undefined && c.action_id === "explore.talk_freeform";
});
const hasHint = computed(
  () => typeof props.card.hint === "string" && props.card.hint.length > 0,
);

function cardActionId() {
  const c = props.card;
  return c.action_code ?? c.action_id ?? "explore.talk_freeform";
}

// The handler is named `activate` (the ui_contract source gate matches
// `@click="activate"` in this file).
function activate() {
  // Pointer parity: `focus` on every activation (the store's
  // `focusItemByKey`), `activate` on the OOB intent.
  if (props.itemKey) {
    emit("focus", props.itemKey);
  }
  const c = props.card;
  const intent = isFreeform.value
    ? {
        action_id: "explore.talk_freeform",
        payload: {
          npc_id: (c.params && c.params.npc_id) ?? c.npc_id ?? null,
          speech: c.label,
        },
      }
    : { action_id: cardActionId(), payload: { ...(c.params || {}) } };
  emit("activate", props.itemKey || c.key || c.label);
  emit("action", intent);
}
</script>

<template>
  <button
    :id="id"
    type="button"
    class="option-card"
    :class="[
      isFreeform ? 'option-card-freeform' : 'option-card-known',
      { 'option-card--focused': focused },
    ]"
    :role="rowMode ? 'option' : null"
    :tabindex="rowMode ? '-1' : '0'"
    :aria-selected="rowMode ? focused : null"
    :data-item-key="rowMode ? itemKey : null"
    data-testid="option-card"
    @click="activate"
  >
    <span class="option-card-glyph" aria-hidden="true">
      {{ isFreeform ? '💬' : '⚡' }}
    </span>
    <span class="option-card-text">
      <span class="option-card-label">{{ card.label }}</span>
      <span v-if="hasHint" class="option-card-hint">{{ card.hint }}</span>
    </span>
  </button>
</template>

<style scoped>
/* H3 (task 5.7): the draft's `.sug` card — a flex row with a tinted icon
   slot, the label plus the hint line. In `rowMode` the card is a listbox
   option (role="option" + the row id); the plain choice-point usage keeps
   the button behavior unchanged. */
.option-card {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  box-sizing: border-box;
  max-width: 16rem;
  padding: 11px 13px;
  color: var(--paper-100);
  background: linear-gradient(180deg, var(--panel-hi), var(--panel));
  border: 1px solid var(--ink-600);
  border-radius: 11px;
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  line-height: 1.5;
  text-align: left;
  cursor: pointer;
  transition: all 0.12s;
}

.option-card:hover,
.option-card:focus-visible {
  border-color: var(--gold-500);
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}

.option-card-glyph {
  flex: none;
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: rgba(207, 68, 68, 0.13);
  border: 1px solid rgba(207, 68, 68, 0.4);
}

.option-card-freeform .option-card-glyph {
  background: rgba(203, 161, 53, 0.13);
  border-color: rgba(203, 161, 53, 0.4);
}

.option-card--focused {
  border-color: var(--gold-500);
  background: var(--panel-hi);
}

.option-card-label {
  display: block;
  font-size: 14px;
  color: var(--paper-50);
  font-weight: 600;
  line-height: 1.2;
}

.option-card-hint {
  display: block;
  font-size: 11px;
  color: var(--paper-500);
  margin-top: 4px;
  line-height: 1.35;
}
</style>
