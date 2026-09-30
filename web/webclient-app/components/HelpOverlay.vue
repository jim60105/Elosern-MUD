<script setup>
// HelpOverlay (B5 full-overlays family, H5 rework): the body content of the
// shared full-screen overlay surface. The modal chrome (position, z-index,
// close button, aria-modal) now belongs to the OverlayHost. The body
// renders the client's own control reference — the keys this client binds,
// the dock's navigation model and the close paths — grouped by where the
// keys act, from the single client-owned source `lib/controls-reference.js`,
// with one line stating how the game's own `help` output is reached. No
// authored game-help content is invented here.
import { controlsReferenceSection } from "../lib/controls-reference.js";

const controlSection = controlsReferenceSection();
</script>

<template>
  <div class="help-overlay-body" data-testid="help-overlay">
    <!-- The client's own control reference (task 6.6): the single
         client-owned source, not authored game-help content. -->
    <div class="help-controls" data-testid="help-controls">
      <section
        v-for="section in controlSection.sections"
        :key="section.id"
        class="help-controls__section"
        :aria-labelledby="`help-section-${section.id}`"
      >
        <h3 :id="`help-section-${section.id}`" class="help-controls__title">{{ section.title }}</h3>
        <dl class="help-controls__list">
          <div
            v-for="entry in section.entries"
            :key="entry.id"
            class="help-controls__row"
            :data-testid="`help-controls-row-${entry.id}`"
          >
            <dt class="help-controls__term">
              <span class="help-controls__keys">
                <template v-for="(key, index) in entry.keys" :key="index">
                  <span v-if="key === '…'" class="help-controls__range" aria-label="至">…</span>
                  <kbd v-else class="help-controls__key" :class="{ 'help-controls__key--glyph': /[^\x20-\x7e]/.test(key) }">{{ key }}</kbd>
                </template>
              </span>
              <span class="help-controls__label">{{ entry.label }}</span>
            </dt>
            <dd class="help-controls__detail">{{ entry.detail }}</dd>
          </div>
        </dl>
      </section>
    </div>
    <p class="help-controls__gamehelp" data-testid="help-controls-gamehelp">
      {{ controlSection.gameHelpPath.before }}<code class="help-controls__command">{{ controlSection.gameHelpPath.command }}</code>{{ controlSection.gameHelpPath.after }}
    </p>
  </div>
</template>

<style scoped>
.help-overlay-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
  font-family: var(--f-sans);
}

/* Three groups side by side at the reference width, each a quiet column of
   rows; narrower workspaces fold them. */
.help-controls {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr));
  gap: 20px 28px;
  align-items: start;
}

.help-controls__section {
  min-width: 0;
}

/* The group heading: serif gold over the gold hairline the drawer headers
   use, fading out to the right. */
.help-controls__title {
  position: relative;
  margin: 0 0 10px;
  padding: 0 0 10px 18px;
  font-family: var(--f-serif);
  font-size: var(--text-xl);
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--gold-400);
}

.help-controls__title::before {
  content: "";
  position: absolute;
  left: 2px;
  top: 0.62em;
  width: 7px;
  height: 7px;
  border: 1px solid var(--gold-500);
  transform: rotate(45deg);
}

.help-controls__title::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 1px;
  background: linear-gradient(90deg, var(--gold-500), rgba(199, 154, 74, 0));
  opacity: 0.6;
}

.help-controls__list {
  margin: 0;
  display: flex;
  flex-direction: column;
}

.help-controls__row {
  padding: 12px 4px 13px;
  border-bottom: 1px solid var(--ink-700);
}

.help-controls__row:last-child {
  border-bottom: 0;
}

.help-controls__term {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 12px;
}

.help-controls__keys {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

/* A key cap: an ink key with a gold legend and a heavier bottom edge. */
.help-controls__key {
  min-width: 26px;
  padding: 2px 7px 3px;
  text-align: center;
  color: var(--gold-300);
  background: var(--ink-860);
  border: 1px solid var(--ink-600);
  border-bottom-width: 2px;
  border-radius: 5px;
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  line-height: 1.4;
}

/* Non-ASCII legends (⌨, 日誌, arrows) read at text size in the sans face; the
   monospace face draws some of them as tiny fallback glyphs. */
.help-controls__key--glyph {
  font-family: var(--f-sans);
  font-size: var(--text-md);
  line-height: 1.3;
}

.help-controls__range {
  color: var(--paper-500);
  font-size: var(--text-sm);
}

.help-controls__label {
  font-size: var(--text-base);
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--paper-50);
}

.help-controls__detail {
  margin: 6px 0 0;
  font-size: var(--text-md);
  line-height: 1.75;
  color: var(--paper-300);
}

.help-controls__gamehelp {
  margin: 0;
  padding: 14px 18px;
  color: var(--paper-300);
  border: 1px solid var(--ink-700);
  border-left: 2px solid var(--gold-500);
  border-radius: var(--radius-sm);
  background: var(--panel-hi);
  font-size: var(--text-md);
  line-height: 1.75;
}

.help-controls__command {
  padding: 1px 6px;
  color: var(--gold-400);
  background: var(--ink-900);
  border: 1px solid var(--ink-600);
  border-radius: 4px;
  font-family: var(--f-mono);
  font-size: var(--text-sm);
}
</style>
