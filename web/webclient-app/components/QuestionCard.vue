<script setup>
// QuestionCard (exploration-room-actions design D5): a small modal yes/no
// question in the centred card frame — the wait card's 進入夢境協作？ before
// a sleep is sent. It wears ChoiceCard's frame (the `choice-card` block: the
// gold frame, crest, corner brackets, and entrance) with its own two-button
// layout and a ✕ close control at its top right.
//
// It is passive: 是 emits `yes`, 否 emits `no`, and the close control or
// Escape emits `close`. Focus is trapped inside it (Tab and Shift+Tab cycle
// through its controls) and starts on `initialFocus` (是 by default; 否 for a
// question whose safe answer is no, webclient-combat-cross-side-confirm). While
// `locked` (a mutation in flight or awaiting its declared revision) 是 is
// disabled — and 否 too unless `noWhileLocked` — and the card states `reason`;
// the close control always works. `tone="caution"` marks a question about an
// unusual, deliberate choice: a seal-red crest, an emblem and a caption, with
// 否 drawn as the safe primary answer. Every key it handles is consumed before
// it can reach the document keyboard bridge.
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
  // Which answer takes focus on mount and when a lock releases.
  initialFocus: {
    type: String,
    default: "yes",
    validator: (value) => value === "yes" || value === "no",
  },
  // Keep 否 working while locked (only 是 waits for the lock).
  noWhileLocked: { type: Boolean, default: false },
  // "default" | "caution": the visual treatment (see above).
  tone: { type: String, default: "default" },
  // A short decorative caption above the question (caution tone).
  caption: { type: String, default: null },
  // The server-authored consequence text of a deliberate operation
  // (webclient-party-exit-confirmation): rendered under the question,
  // verbatim and with its authored line breaks, and part of the card's
  // accessible description.
  detail: { type: String, default: null },
});

const emit = defineEmits(["yes", "no", "close"]);

const rootRef = ref(null);
const yesRef = ref(null);
const noRef = ref(null);
const titleId = useId();
const reasonId = useId();
const detailId = useId();
const still = !props.entrance;

const shownReason = computed(() => (props.locked && props.reason ? props.reason : null));
const shownDetail = computed(() => (typeof props.detail === "string" && props.detail !== "" ? props.detail : null));
const describedBy = computed(() => [shownDetail.value ? detailId : null, shownReason.value ? reasonId : null].filter(Boolean).join(" ") || null);

function controls() {
  return Array.from(rootRef.value?.querySelectorAll("button:not([disabled])") || []);
}

const noLocked = computed(() => props.locked && !props.noWhileLocked);

function focusFirst() {
  const preferred = props.initialFocus === "no" ? noRef.value : yesRef.value;
  const first = preferred && !preferred.disabled ? preferred : controls()[0];
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

// A lock that disables the focused answer leaves focus on the card, never on
// the body; the lock releasing returns it to the initial answer.
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
  const preferred = props.initialFocus === "no" ? !noLocked.value : !props.locked;
  if (preferred) {
    focusFirst();
  } else {
    rootRef.value?.focus({ preventScroll: true });
  }
});

defineExpose({ focus: focusFirst });
</script>

<template>
  <div
    ref="rootRef"
    class="choice-card question-card"
    :class="{ 'choice-card--still': still, 'question-card--caution': tone === 'caution', 'question-card--safe-no': initialFocus === 'no' }"
    :data-tone="tone"
    role="dialog"
    aria-modal="true"
    :aria-labelledby="titleId"
    :aria-describedby="describedBy"
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
    <div v-if="tone === 'caution'" class="question-card__emblem" aria-hidden="true">
      <svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M16 3.5l11 4.2v7.6c0 6.4-4.6 11.2-11 13.2C9.6 26.5 5 21.7 5 15.3V7.7z" />
        <path d="M11.2 11.2l9.6 9.6M20.8 11.2l-9.6 9.6" />
      </svg>
    </div>
    <p v-if="caption" class="question-card__caption" aria-hidden="true">{{ caption }}</p>
    <p :id="titleId" class="question-card__question" data-testid="question-card-question">{{ question }}</p>
    <p
      v-if="shownDetail"
      :id="detailId"
      class="question-card__detail"
      data-testid="question-card-detail"
    >{{ shownDetail }}</p>
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
        ref="noRef"
        type="button"
        class="question-card__answer question-card__answer--no"
        data-testid="question-card-no"
        :disabled="noLocked"
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

/* The server-authored consequence: its own line breaks are meaningful (the
   operation's scope and what it costs), so it keeps them. */
.question-card__detail {
  margin: 0;
  text-align: center;
  white-space: pre-line;
  font: var(--text-sm)/1.5 var(--f-sans);
  color: var(--paper-300);
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

/* The caution tone (webclient-combat-cross-side-confirm): the same frame with
   (each rule doubles the `choice-card` class, so it wins over the frame's
   own rules whichever stylesheet loads last)
   a seal-red crest and lozenge, a warm red wash from the top, a small shield
   emblem and a spaced caption, so the question reads as "think twice" by
   shape and text as well as by hue. 否 is the safe answer: it carries the
   gold primary fill, while 是 takes a quiet seal-red outline. */
.choice-card.question-card--caution {
  background:
    radial-gradient(110% 70% at 50% 0%, rgba(207, 68, 68, 0.16), transparent 68%),
    linear-gradient(180deg, rgba(30, 22, 24, 0.96), rgba(12, 12, 16, 0.96));
  border-color: rgba(207, 68, 68, 0.5);
  padding-top: calc(22px * var(--ui-scale));
  gap: calc(10px * var(--ui-scale));
}
.choice-card.question-card--caution::before {
  background: linear-gradient(90deg, transparent, var(--seal-400), transparent);
}
.choice-card.question-card--caution::after {
  background: var(--seal-400);
  box-shadow: 0 0 calc(10px * var(--ui-scale)) var(--seal-glow);
}
.choice-card.question-card--caution .choice-card__corners {
  --corner: rgba(224, 107, 107, 0.85);
}
.choice-card.question-card--caution:focus-visible {
  border-color: rgba(224, 107, 107, 0.78);
}
.question-card__emblem {
  align-self: center;
  display: grid;
  place-items: center;
  width: calc(36px * var(--ui-scale));
  height: calc(36px * var(--ui-scale));
  color: var(--seal-400);
  filter: drop-shadow(0 0 calc(6px * var(--ui-scale)) var(--seal-glow));
}
.question-card__emblem svg {
  width: 100%;
  height: 100%;
}
.question-card__caption {
  margin: 0;
  text-align: center;
  font: var(--text-xs)/1.4 var(--f-sans);
  letter-spacing: 0.32em;
  /* Balance the trailing letter-spacing so the caption sits centred. */
  text-indent: 0.32em;
  color: var(--seal-400);
}
.question-card--caution .question-card__question {
  padding: 0 calc(4px * var(--ui-scale));
  /* A line breaks only at the punctuation (before 〈), never inside 使用 or
     a skill name; a name too long for the line still wraps. */
  word-break: keep-all;
  overflow-wrap: anywhere;
  text-wrap: balance;
}
.question-card--caution .question-card__answers {
  margin-top: calc(4px * var(--ui-scale));
}
.question-card--safe-no .question-card__answer--yes {
  border-color: rgba(207, 68, 68, 0.55);
  background: transparent;
  color: var(--paper-100);
}
.question-card--safe-no .question-card__answer--yes:hover:not(:disabled),
.question-card--safe-no .question-card__answer--yes:focus-visible {
  border-color: var(--seal-400);
  background: rgba(207, 68, 68, 0.16);
  box-shadow: 0 0 0 1px var(--seal-400);
}
.question-card--safe-no .question-card__answer--no {
  border-color: var(--gold-600);
  background: rgba(185, 154, 96, 0.14);
  color: var(--paper-50);
}
.question-card--safe-no .question-card__answer--yes:disabled {
  border-style: dashed;
  border-color: var(--ink-600);
  background: transparent;
  color: var(--paper-500);
  box-shadow: none;
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
