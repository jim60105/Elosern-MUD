<script setup>
// QuestionCard (exploration-room-actions design D5): a small modal yes/no
// question in the centred card frame — the wait card's 進入夢境協作？ before
// a sleep is sent. It wears ChoiceCard's frame (the `choice-card` block: the
// gold frame, crest, corner brackets, and entrance) with its own two-button
// layout and a ✕ close control at its top right.
//
// It is passive: 是 emits `yes`, 否 emits `no`, and the close control or
// Escape emits `close`. Focus is trapped inside it (Tab and Shift+Tab cycle
// through its controls) and starts on 是. While `locked` (a mutation in
// flight or awaiting its declared revision) 是 and 否 are disabled and the
// card states `reason`; the close control always works. Every key it handles
// is consumed before it can reach the document keyboard bridge.
import { computed, nextTick, onMounted, ref, useId, watch } from "vue";

const props = defineProps({
  question: { type: String, required: true },
  yesLabel: { type: String, default: "是" },
  noLabel: { type: String, default: "否" },
  closeLabel: { type: String, default: "取消" },
  locked: { type: Boolean, default: false },
  reason: { type: String, default: null },
  // Whether the card animates in when it mounts.
  entrance: { type: Boolean, default: true },
  testId: { type: String, default: "question-card" },
});

const emit = defineEmits(["yes", "no", "close"]);

const rootRef = ref(null);
const yesRef = ref(null);
const titleId = useId();
const reasonId = useId();
const still = !props.entrance;

const shownReason = computed(() => (props.locked && props.reason ? props.reason : null));

function controls() {
  return Array.from(rootRef.value?.querySelectorAll("button:not([disabled])") || []);
}

function focusFirst() {
  const first = yesRef.value && !yesRef.value.disabled ? yesRef.value : controls()[0];
  first?.focus({ preventScroll: true });
}

function onKeydown(event) {
  if (event.ctrlKey || event.altKey || event.metaKey) {
    return;
  }
  if (event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    emit("close");
    return;
  }
  if (event.key === "Tab") {
    event.preventDefault();
    event.stopPropagation();
    const list = controls();
    if (list.length === 0) {
      rootRef.value?.focus({ preventScroll: true });
      return;
    }
    const index = list.indexOf(document.activeElement);
    const step = event.shiftKey ? -1 : 1;
    const next = index < 0 ? (event.shiftKey ? list.length - 1 : 0) : (index + step + list.length) % list.length;
    list[next].focus({ preventScroll: true });
    return;
  }
  // Enter / Space reach the focused button natively; every other key stays
  // inside the question.
  if (event.key !== "Enter" && event.key !== " ") {
    event.stopPropagation();
  }
}

// A lock that disables the focused 是 leaves focus on the card, never on the
// body; the lock releasing returns it to 是.
watch(
  () => props.locked,
  async (locked) => {
    await nextTick();
    const active = document.activeElement;
    if (locked && (!active || !rootRef.value?.contains(active) || active.disabled)) {
      rootRef.value?.focus({ preventScroll: true });
    } else if (!locked && active === rootRef.value) {
      focusFirst();
    }
  },
);

onMounted(() => {
  if (props.locked) {
    rootRef.value?.focus({ preventScroll: true });
  } else {
    focusFirst();
  }
});

defineExpose({ focus: focusFirst });
</script>

<template>
  <div
    ref="rootRef"
    class="choice-card question-card"
    :class="{ 'choice-card--still': still }"
    role="dialog"
    aria-modal="true"
    :aria-labelledby="titleId"
    :aria-describedby="shownReason ? reasonId : null"
    tabindex="-1"
    :data-testid="testId"
    @keydown="onKeydown"
  >
    <span class="choice-card__corners" aria-hidden="true"></span>
    <button
      type="button"
      class="question-card__close"
      :aria-label="closeLabel"
      :title="closeLabel"
      data-testid="question-card-close"
      @click="emit('close')"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
        <path d="M7 7l10 10M17 7L7 17" />
      </svg>
    </button>
    <p :id="titleId" class="question-card__question" data-testid="question-card-question">{{ question }}</p>
    <p
      v-if="shownReason"
      :id="reasonId"
      class="question-card__reason"
      data-testid="question-card-reason"
    >{{ shownReason }}</p>
    <div class="question-card__answers">
      <button
        ref="yesRef"
        type="button"
        class="question-card__answer question-card__answer--yes"
        data-testid="question-card-yes"
        :disabled="locked"
        @click="emit('yes')"
      >{{ yesLabel }}</button>
      <button
        type="button"
        class="question-card__answer"
        data-testid="question-card-no"
        :disabled="locked"
        @click="emit('no')"
      >{{ noLabel }}</button>
    </div>
  </div>
</template>

<style>
/* The question in the card frame: a short serif question, two answers side
   by side, and the close control in the top right corner. */
.question-card {
  align-self: center;
  width: min(100%, calc(360px * var(--ui-scale)));
  padding: calc(26px * var(--ui-scale)) calc(24px * var(--ui-scale)) calc(20px * var(--ui-scale));
  gap: calc(14px * var(--ui-scale));
  align-items: stretch;
}

.question-card:focus-visible {
  border-color: rgba(228, 200, 142, 0.72);
}

.question-card__question {
  margin: 0;
  text-align: center;
  font-family: var(--f-serif);
  font-size: clamp(18px * var(--ui-scale), 2vh, 21px * var(--ui-scale));
  line-height: 1.4;
  letter-spacing: 0.08em;
  color: var(--paper-50);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
}

.question-card__reason {
  margin: 0;
  text-align: center;
  font: var(--text-sm)/1.45 var(--f-sans);
  color: var(--paper-400);
}

.question-card__answers {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: calc(10px * var(--ui-scale));
}

.question-card__answer {
  min-height: calc(40px * var(--ui-scale));
  padding: 0 calc(14px * var(--ui-scale));
  border: 1px solid #736b5c;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--paper-100);
  font: var(--text-md)/1 var(--f-sans);
  letter-spacing: 0.12em;
  cursor: pointer;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard);
}

.question-card__answer--yes {
  border-color: var(--gold-600);
  background: rgba(185, 154, 96, 0.12);
  color: var(--paper-50);
}

.question-card__answer:hover:not(:disabled),
.question-card__answer:focus-visible {
  border-color: var(--gold-400);
  background: var(--gold-glow);
  color: var(--paper-50);
  outline: none;
}

.question-card__answer:focus-visible {
  box-shadow: 0 0 0 1px var(--gold-400);
}

.question-card__answer:disabled {
  border-style: dashed;
  border-color: var(--ink-600);
  background: transparent;
  color: var(--paper-500);
  cursor: default;
}

.question-card__close {
  position: absolute;
  top: calc(8px * var(--ui-scale));
  right: calc(8px * var(--ui-scale));
  z-index: 2;
  display: grid;
  place-items: center;
  width: calc(28px * var(--ui-scale));
  height: calc(28px * var(--ui-scale));
  padding: 0;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--paper-400);
  cursor: pointer;
}

.question-card__close svg {
  width: calc(14px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
}

.question-card__close:hover,
.question-card__close:focus-visible {
  border-color: var(--gold-500);
  color: var(--paper-50);
  outline: none;
}
</style>
