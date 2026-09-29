<script setup>
// DrawerHeader (webclient-drawer-frame-unification): the one presentational
// header every reference surface shares — the reference drawers (HudDrawer,
// including the gallery's nested editors) and the utility overlays
// (OverlayHost). It draws the surface's registry glyph, its title, an
// optional subtitle, and one icon-only 36px close control, and emits
// `close` only. It owns no focus trap, no Escape handling, no opener record
// and no open-surface registration: each host keeps its own modal lifecycle
// and only borrows this markup. The glyph comes from the same registry the
// top navigation draws from, so a header always matches the control that
// opened its surface.
import { ref } from "vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";

defineProps({
  // A `dock-icons.js` glyph key; unmapped or null renders no glyph.
  icon: { type: String, default: null },
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
  // The host's test-id stem (`hud-drawer` | `overlay-host`): the close
  // control is `<surface>-close`, the title `<surface>__title`.
  surface: { type: String, required: true },
  // A host kept mounted while closed takes its close control out of the
  // tab order.
  closeTabindex: { type: Number, default: 0 },
});
const emit = defineEmits(["close"]);

// The host moves focus to the close control when it opens (HudDrawer's
// trap `initialFocusEl`).
const closeButton = ref(null);
defineExpose({ closeButton });
</script>

<template>
  <header class="drawer-header">
    <span v-if="icon && glyphPath(icon)" class="drawer-header__icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" width="18" height="18">
        <path :d="glyphPath(icon)" stroke="currentColor" stroke-width="1.7" v-bind="glyphAttrs(icon)" />
      </svg>
    </span>
    <h3 class="drawer-header__title" :data-testid="`${surface}__title`">{{ title }}</h3>
    <p v-if="subtitle" class="drawer-header__subtitle" :title="subtitle">{{ subtitle }}</p>
    <button
      ref="closeButton"
      type="button"
      class="drawer-header__close"
      :data-testid="`${surface}-close`"
      :tabindex="closeTabindex"
      aria-label="關閉"
      @click="emit('close')"
    >
      <svg viewBox="0 0 24 24" fill="none" width="16" height="16" aria-hidden="true">
        <path :d="glyphPath('close')" stroke="currentColor" stroke-width="1.8" v-bind="glyphAttrs('close')" />
      </svg>
    </button>
  </header>
</template>

<style>
/* Selectors are qualified by `.drawer-header` so a host's broad element
   rules (the gallery's `.gallery-ui h3` / `button`) never restyle the shared
   header. One header row: glyph medallion, serif title, muted subtitle on the same
   baseline, the close control pushed to the far edge. The gold hairline
   under it fades out from the title side (the band's gold edge, A7). */
.drawer-header {
  position: relative;
  flex: none;
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 60px;
  box-sizing: border-box;
  padding: 10px 14px 10px 20px;
  background: linear-gradient(180deg, #1a1c20, #121418);
}

.drawer-header::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 1px;
  background: linear-gradient(90deg, #cfb3787a, #cfb37826 38%, var(--ink-700) 72%);
  pointer-events: none;
}

.drawer-header .drawer-header__icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  color: var(--gold-400);
  background: radial-gradient(circle at 50% 35%, #2a261e, #15161a 70%);
  box-shadow: inset 0 0 0 1px #cfb37855, 0 0 10px -4px var(--gold-glow);
}

.drawer-header .drawer-header__title {
  margin: 0;
  min-width: 0;
  color: var(--gold-400);
  font-family: var(--f-serif);
  font-size: var(--text-2xl);
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: .06em;
  overflow-wrap: anywhere;
}

.drawer-header .drawer-header__subtitle {
  margin: 0;
  min-width: 0;
  padding-left: 12px;
  border-left: 1px solid var(--ink-700);
  color: var(--paper-500);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  letter-spacing: .04em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.drawer-header .drawer-header__close {
  flex: none;
  margin-left: auto;
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  padding: 0;
  color: var(--paper-300);
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: color var(--motion-fast) var(--ease-standard), border-color var(--motion-fast) var(--ease-standard);
}

.drawer-header .drawer-header__close:hover {
  color: var(--gold-400);
  border-color: var(--gold-500);
}

.drawer-header .drawer-header__close:focus-visible {
  outline: none;
  color: var(--gold-400);
  border-color: var(--gold-400);
  box-shadow: var(--focus);
}
</style>
