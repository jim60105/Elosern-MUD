<script setup>
// HelpOverlay (B5 full-overlays family): a full-viewport help dialog
// backed by the game-authored onboarding guide — the arrival scene, the
// South-Gate guard's scripted guidance, and the keyword Q&A set. The
// `guide` prop is a read-only data slice: text renders as plain text
// nodes (no markup pipeline), and the component renders only what the
// data gives — a missing `guide` or a null section shows just the dialog
// frame, never invented copy. The close button is a client-local intent:
// it emits "close"; the shell/store owns the open state via the `open`
// prop.
const emit = defineEmits(["close"]);

defineProps({
  open: {
    type: Boolean,
    default: true,
  },
  guide: {
    type: Object,
    default: () => ({}),
  },
});
</script>

<template>
  <section
    v-if="open"
    class="elosern help-overlay"
    role="dialog"
    aria-modal="true"
    aria-label="遊戲說明"
    data-testid="help-overlay"
  >
    <button
      type="button"
      class="help-overlay__close"
      data-testid="help-overlay-close"
      @click="emit('close')"
    >
      關閉
    </button>

    <div
      v-if="guide.arrival"
      class="help-section"
      data-testid="help-arrival"
    >
      <h2 class="help-section__title">抵達</h2>
      <p class="help-section__prose">{{ guide.arrival.prose }}</p>
      <p class="help-section__prompt" data-testid="help-arrival-prompt">
        {{ guide.arrival.prompt }}
      </p>
    </div>

    <div
      v-if="guide.guard"
      class="help-section"
      data-testid="help-guard"
    >
      <h2 class="help-section__title">守門守衛的指引</h2>
      <p class="help-section__guard">
        {{ guide.guard.name }}：{{ guide.guard.guidance }}
      </p>
    </div>

    <div
      v-if="guide.qna && guide.qna.length"
      class="help-qa"
      data-testid="help-qa"
    >
      <h2 class="help-qa__title">常見問題</h2>
      <div
        v-for="(entry, index) in guide.qna"
        :key="index"
        class="help-qa__row"
        data-testid="help-qa-row"
      >
        <span class="help-qa__question">{{ entry.question }}</span>
        <span class="help-qa__answer">{{ entry.answer }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.help-overlay {
  position: absolute;
  inset: 0;
  z-index: 50;
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
  padding: var(--sp-6);
  background: var(--panel);
  color: var(--paper-100);
}

.help-overlay__close {
  align-self: flex-end;
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  color: var(--paper-100);
  background: var(--ink-700);
  border: var(--line);
  border-radius: var(--radius-sm);
  padding: var(--sp-1) var(--sp-3);
  cursor: pointer;
}

.help-section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  border: var(--line);
  border-radius: var(--radius);
  padding: var(--sp-4);
}

.help-section__title,
.help-qa__title {
  font-family: var(--f-display);
  font-size: var(--text-dialog);
  color: var(--gold-400);
}

.help-section__prose {
  font-family: var(--f-serif);
  font-size: var(--text-narrative);
  line-height: var(--lh-narrative);
  color: var(--paper-50);
}

.help-section__prompt,
.help-section__guard {
  font-family: var(--f-serif);
  font-size: var(--text-dialog);
  color: var(--paper-300);
}

.help-qa {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.help-qa__row {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  border: var(--line);
  border-radius: var(--radius-sm);
  padding: var(--sp-2) var(--sp-3);
}

.help-qa__question {
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--seal-400);
}

.help-qa__answer {
  font-family: var(--f-serif);
  font-size: var(--text-body);
  color: var(--paper-300);
}
</style>
