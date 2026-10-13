<script setup>
// DialogueChoices (webclient-dialogue-choices-overlay D5; AVG stage design
// §8.2): the conversation's choice list, centred over the stage in the
// `choices` anchor once the session line is fully read. Rows, in order: one
// pick per committed `dialogue.choices` entry (digit badge 1–N), then
// `⌨ 自由對話`, `↦ 移動…`, and `✕ 結束對話`. `↦ 移動…` swaps the rows for the
// committed scene overview's exits (direction glyph and destination, a
// disabled exit keeping its server-authored reason) plus a back row.
//
// One keyboard composite, one tab stop: DOM focus rests on the menu
// container, which names its active row through `aria-activedescendant`
// (the dock's pattern). ArrowUp / ArrowDown wrap, Home / End jump, Enter /
// Space activate (a held repeat never does), digits 1–N activate pick N,
// and Escape leaves the exits. Every handled key is consumed before it can
// bubble to the document keyboard bridge; `/`, Tab, and every other key
// pass through untouched. A pointer activation focuses the list and runs
// the same activation path as Enter.
//
// The entrance (webclient-mode-transitions D5; AVG stage design §9.3): the
// card fades in, and each row fades and rises into place one stagger step
// after the one above it. Pure CSS keyframes on elements that are in the
// DOM, focusable, and clickable from their first frame, so no key or
// pointer ever waits for the animation. A view swap (`↦ 移動…` and back)
// renders new rows, which stagger in the same way; the rows they replace
// are removed at once. A list mounted in the frame a reconnect renders
// (`entrance` false) shows at rest.
//
// The initial highlight (webclient-message-typesetting): the list opens
// with its first enabled row active — and the exits view with its first
// enabled exit — shown quietly even while the list does not hold focus (a
// conversation opened by pointer), so the row keyboard navigation starts on
// is visible. It is the same `aria-activedescendant` state the keys move;
// showing it activates nothing and takes no focus.
//
// Passive: activation calls `beforeActivate` (the shell parks focus on the
// message page so the list's removal never drops it) and emits the row's
// intent; the parent owns every dispatch.
import { computed, ref } from "vue";
import ChoiceCard from "./ChoiceCard.vue";
import { directionGlyph, disabledRowReason, exitLabel } from "./dock-exits.js";

const props = defineProps({
  // The dialogue view model's pick rows (`dialogueViewModel(...).picks`).
  picks: { type: Array, default: () => [] },
  // The committed scene overview's exit items, in its order.
  exits: { type: Array, default: () => [] },
  // The committed `localMapModel`, for exit destination names.
  localMap: { type: Object, default: null },
  // A mutation is in flight or awaiting its revision: no activation runs.
  // A component-level safety net: AppClient never renders the list while a
  // dispatch is in flight, so the live wiring does not reach it.
  locked: { type: Boolean, default: false },
  // Called before every emitted activation.
  beforeActivate: { type: Function, default: null },
  // Whether the list animates in when it mounts (false in the frame a
  // reconnect renders, webclient-mode-transitions D2). Read once, at mount.
  entrance: { type: Boolean, default: true },
});

const emit = defineEmits(["pick", "freeform", "move", "leave"]);

const cardRef = ref(null);
const view = ref("choices");

// The card's view model (exploration-presence-rail D1): the shell is
// ChoiceCard; this component keeps the rows, the view swap, and the emits.
const rows = computed(() => {
  if (view.value === "exits") {
    const exitRows = props.exits.map((item, index) => {
      const enabled = item.enabled !== false;
      return {
        kind: "exit",
        key: `exit-${item.key ?? index}`,
        testId: "dialogue-exit-row",
        reasonTestId: "dialogue-exit-reason",
        badge: directionGlyph(item.direction) || "↦",
        label: exitLabel(item, props.localMap),
        enabled,
        reason: enabled ? null : disabledRowReason(item),
        item,
      };
    });
    return [
      ...exitRows,
      { kind: "back", key: "back", testId: "dialogue-exits-back", badge: "↩", label: "返回對話", enabled: true, back: true },
    ];
  }
  return [
    ...props.picks.map((pick, index) => ({
      kind: "pick",
      key: pick.key,
      testId: "dialogue-pick",
      badge: String(index + 1),
      label: pick.label,
      keywordId: pick.payload ? pick.payload.keyword_id : undefined,
      enabled: true,
      pick,
    })),
    { kind: "freeform", key: "freeform", testId: "dialogue-freeform", badge: "⌨", icon: "keyboard", label: "自由對話", enabled: true },
    { kind: "move", key: "move", testId: "dialogue-move", badge: "↦", label: "移動…", enabled: true },
    { kind: "leave", key: "leave", testId: "dialogue-exit", badge: "✕", icon: "close", label: "結束對話", enabled: true },
  ];
});

// The trailing rows of the choice view open with a divider after the picks.
const firstTrailing = computed(() => (view.value === "choices" ? props.picks.length : props.exits.length));

// Swaps the rows; with no index, the new view's first enabled row is active.
function showView(next, index = null) {
  view.value = next;
  if (index === null) {
    // The first enabled row that is not the way back, else the first row.
    const first = rows.value.findIndex((row) => row.enabled && !row.back);
    index = first < 0 ? 0 : first;
  }
  cardRef.value?.setActive(index);
}

function onPick(key) {
  const row = rows.value.find((entry) => entry.key === key);
  if (!row) {
    return;
  }
  // The exits swap is local: it dispatches nothing.
  if (row.kind === "move") {
    showView("exits");
    return;
  }
  if (props.locked) {
    return;
  }
  props.beforeActivate?.();
  if (row.kind === "pick") {
    emit("pick", row.pick);
  } else if (row.kind === "freeform") {
    emit("freeform");
  } else if (row.kind === "leave") {
    emit("leave");
  } else if (row.kind === "exit") {
    emit("move", row.item);
  }
}

// The way back from the exits (its back row or Escape) is local too.
function onBack() {
  if (view.value === "exits") {
    showView("choices", props.picks.length + 1);
  }
}

function focus() {
  cardRef.value?.focus();
}

defineExpose({ focus });
</script>

<template>
  <ChoiceCard
    ref="cardRef"
    block="dialogue-choices"
    test-id="dialogue-choices"
    :rows="rows"
    :view-key="view"
    :trailing-index="firstTrailing"
    :caption="view === 'exits' ? '移動' : null"
    :aria-label="view === 'exits' ? '移動：選擇出口' : '對話選項'"
    :entrance="entrance"
    :escape-back="view === 'exits'"
    :digit-rows="view === 'choices' ? picks.length : 0"
    :claim-digits="false"
    @pick="onPick"
    @back="onBack"
  />
</template>
