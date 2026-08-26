<script setup>
// HelpOverlay (B5 full-overlays family, H5 rework): the body content of the
// shared full-screen overlay surface. The modal chrome (position, z-index,
// close button, aria-modal) now belongs to the OverlayHost. The body
// renders the client's own control reference — the keys this client binds,
// the dock's navigation model, the quick-word chips and the close paths —
// from the single client-owned source `lib/controls-reference.js`, with one
// line stating how the game's own `help` output is reached. The `guide`
// sections render only when a payload supplies them; no authored game-help
// content is invented when the payload is absent.
import { controlsReferenceSection } from "../lib/controls-reference.js";

defineProps({
  // The optional game-authored onboarding guide (arrival, guard guidance,
  // keyword Q&A). Rendered only when present; a missing `guide` or a null
  // section shows just the control reference, never invented copy.
  guide: {
    type: Object,
    default: () => ({}),
  },
});

const controlSection = controlsReferenceSection();
</script>

<template>
  <div class="help-overlay-body" data-testid="help-overlay">
    <!-- The client's own control reference (task 6.6): the single
         client-owned source, not authored game-help content. -->
    <section class="help-controls" data-testid="help-controls">
      <h2 class="help-controls__title">操作參考</h2>
      <div
        v-for="entry in controlSection.entries"
        :key="entry.key"
        class="help-controls__row"
        :data-testid="`help-controls-row-${entry.key}`"
      >
        <span class="help-controls__key">{{ entry.key }}</span>
        <span class="help-controls__label">{{ entry.label }}</span>
        <span class="help-controls__detail">{{ entry.detail }}</span>
      </div>
      <p class="help-controls__gamehelp" data-testid="help-controls-gamehelp">
        {{ controlSection.gameHelpPath }}
      </p>
    </section>

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
  </div>
</template>

<style scoped>
.help-overlay-body {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.help-controls {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.help-controls__title,
.help-qa__title {
  margin: 0;
  font-family: var(--f-display);
  font-size: var(--text-dialog);
  color: var(--gold-400);
}

.help-controls__row {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: var(--sp-2) var(--sp-3);
  padding: var(--sp-2) var(--sp-3);
  border: var(--line);
  border-radius: var(--radius-sm);
}

.help-controls__key {
  grid-row: span 2;
  padding: 2px var(--sp-2);
  color: var(--paper-50);
  background: var(--panel-hi);
  border: var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  align-self: start;
}

.help-controls__label {
  font-family: var(--f-sans);
  font-size: var(--text-body);
  font-weight: 600;
  color: var(--paper-50);
}

.help-controls__detail {
  grid-column: 2;
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  color: var(--paper-500);
}

.help-controls__gamehelp {
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-300);
  background: var(--panel-hi);
  border: var(--line);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}

.help-section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  border: var(--line);
  border-radius: var(--radius);
  padding: var(--sp-4);
}

.help-section__title {
  margin: 0;
  font-family: var(--f-display);
  font-size: var(--text-dialog);
  color: var(--gold-400);
}

.help-section__prose {
  margin: 0;
  font-family: var(--f-serif);
  font-size: var(--text-narrative);
  line-height: var(--lh-narrative);
  color: var(--paper-50);
}

.help-section__prompt,
.help-section__guard {
  margin: 0;
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
