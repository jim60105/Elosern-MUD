<script setup>
// HelpOverlay (B5 full-overlays family, H5 rework): the body content of the
// shared full-screen overlay surface. The modal chrome (position, z-index,
// close button, aria-modal) now belongs to the OverlayHost. The body
// renders the client's own control reference — the keys this client binds,
// the dock's navigation model, the quick-word chips and the close paths —
// from the single client-owned source `lib/controls-reference.js`, with one
// line stating how the game's own `help` output is reached. No authored
// game-help content is invented here.
import { controlsReferenceSection } from "../lib/controls-reference.js";

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

.help-controls__title {
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
</style>
