<script setup>
// EmptyState (webclient-drawer-content-polish): the one presentational body
// an AVAILABLE but empty drawer list shows — a decorative line glyph from the
// shared registry, a short headline and one line of guidance in a solid ink
// frame. It carries no action of its own: a host passes an existing, real
// control through the default slot when it has one. It is never used for an
// unavailable panel, whose registry-owned reason stays its own distinct
// paragraph, so "empty" and "unavailable" always read differently. The host's
// `data-testid` falls through to the root.
import { glyphAttrs, glyphPath } from "./dock-icons.js";

defineProps({
  // A `dock-icons.js` glyph key; unmapped or null renders no glyph.
  glyph: { type: String, default: null },
  headline: { type: String, required: true },
  guidance: { type: String, default: "" },
});
</script>

<template>
  <div class="empty-state">
    <span v-if="glyph && glyphPath(glyph)" class="empty-state__glyph" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" width="22" height="22">
        <path :d="glyphPath(glyph)" stroke="currentColor" stroke-width="1.5" v-bind="glyphAttrs(glyph)" />
      </svg>
    </span>
    <p class="empty-state__headline">{{ headline }}</p>
    <p v-if="guidance" class="empty-state__guidance">{{ guidance }}</p>
    <div v-if="$slots.default" class="empty-state__actions">
      <slot />
    </div>
  </div>
</template>

<style>
/* Qualified by `.empty-state` so a host's broad element rules never restyle
   it. A solid ink card — not a dashed "missing" box — centred on its glyph. */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-2);
  box-sizing: border-box;
  margin: 0;
  padding: var(--sp-6) var(--sp-5);
  text-align: center;
  background: var(--ink-900);
  border: 1px solid var(--ink-700);
  border-radius: var(--radius);
}

.empty-state .empty-state__glyph {
  display: grid;
  place-items: center;
  width: calc(44px * var(--ui-scale));
  height: calc(44px * var(--ui-scale));
  margin-bottom: var(--sp-1);
  border-radius: 50%;
  color: var(--gold-600);
  box-shadow: inset 0 0 0 1px #8f713c66;
  background: radial-gradient(circle at 50% 35%, #1f1c17, var(--ink-900) 70%);
}

.empty-state .empty-state__headline {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-serif);
  font-size: var(--text-lg);
  letter-spacing: .08em;
}

.empty-state .empty-state__guidance {
  margin: 0;
  max-width: 36em;
  color: var(--paper-500);
  font-family: var(--f-sans);
  font-size: var(--text-md);
  line-height: 1.7;
}

.empty-state .empty-state__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--sp-2);
  margin-top: var(--sp-2);
}

/* The icon's width/height attributes are its reference size; the chrome
   factor scales the drawn box with its control (webclient-proportional-ui-scale). */
.empty-state__glyph svg {
  width: calc(22px * var(--ui-scale));
  height: calc(22px * var(--ui-scale));
}
</style>
