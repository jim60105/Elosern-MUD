<script setup>
// HudFrame (H1, webclient-hud-01-shell-and-scene, design D1/D2/D7/D9/D10):
// the full-bleed cinematic stage. A `position:relative; overflow:hidden`
// root with named, absolutely-positioned HUD anchors: `hud-left`, `hud-right`,
// `feed`, `dock`, and `command-line`. Mode gating is CSS-only on the
// `data-elosern-mode` attribute (the single source for the committed mode),
// using `display:none` so hidden surfaces leave the accessibility tree and
// the tab order (REDESIGN.md §0.1: 不顯示的絕對隱藏，不是灰掉). The scene
// backdrop renders as the lowest stage layer (z 0); the vignette sits above
// it (z 1); the caption (z 3), the HUD islands (z 4), the dock (z 5), and
// the command line (z 6) layer above.
//
// The open-surface registry (design D9): a drawer or full-screen overlay
// marks the stage `menu-open` so the surfaces behind it are visually
// recessed; the mark clears only when no open surface remains.
import { computed } from "vue";

const props = defineProps({
  // The committed mode value rendered on the shell root. The store's reducer
  // modes are "exploration", "combat", and "creation".
  mode: { type: String, default: "exploration" },
  // The open-surface registry for the stage recession (design D9). The set
  // of currently open surface names (e.g. "drawer", "full-log", "creation").
  openSurfaces: { type: Array, default: () => [] },
  // The low-HP flag (design D7): H2 supplies the state from the status
  // payload; H1 ships the CSS hook, defaulting off.
  lowhp: { type: Boolean, default: false },
});

// The open-surface registry drives the `menu-open` mark (design D9): the
// mark clears only when no surface remains open.
const menuOpen = computed(() => props.openSurfaces.length > 0);

defineExpose({ menuOpen });
</script>

<template>
  <div
    class="elosern-stage"
    data-testid="elosern-stage"
    :data-elosern-mode="mode"
    :data-menu-open="menuOpen"
    :data-lowhp="lowhp ? 'true' : 'false'"
  >
    <div class="stage-vignette" data-testid="stage-vignette"></div>
    <div
      class="stage-combat-veil"
      data-testid="stage-combat-veil"
      :data-mode="mode"
    ></div>
    <slot name="backdrop" />
    <div
      class="stage-anchor"
      data-anchor="hud-left"
      data-testid="anchor-hud-left"
    >
      <slot name="hud-left" />
    </div>
    <div
      class="stage-anchor"
      data-anchor="hud-right"
      data-testid="anchor-hud-right"
    >
      <slot name="hud-right" />
    </div>
    <div
      class="stage-anchor"
      data-anchor="feed"
      data-testid="anchor-feed"
    >
      <slot name="feed" />
    </div>
    <div
      class="stage-anchor"
      data-anchor="dock"
      data-testid="anchor-dock"
    >
      <slot name="dock" />
    </div>
    <div
      class="stage-anchor"
      data-anchor="command-line"
      data-testid="anchor-command-line"
    >
      <slot name="command-line" />
    </div>
  </div>
</template>

<style>
.elosern-stage {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

/* The scene backdrop (the `backdrop` slot content) is the lowest stage
   layer (z-index 0). The vignette and the combat veil sit just above it. */
.elosern-stage .stage-vignette {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  border-radius: 2px;
  box-shadow: var(--vignette);
  transition: box-shadow var(--motion-base) var(--ease-standard);
}
.elosern-stage[data-lowhp="true"] .stage-vignette {
  box-shadow: var(--vignette-lowhp);
}

/* The combat pulse (H2 supplies the low-HP and combat state; H1 ships the
   hooks — design D7). */
.elosern-stage[data-elosern-mode="combat"] .stage-combat-veil {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  background: var(--stage-combat-veil);
  animation: elosern-combat-pulse var(--motion-pulse) ease-in-out infinite;
}
.elosern-stage:not([data-elosern-mode="combat"]) .stage-combat-veil {
  display: none;
}

/* Named anchors (design D1/D10): absolutely positioned, bounded. */
.elosern-stage .stage-anchor {
  position: absolute;
  box-sizing: border-box;
}

/* hud-left: the HUD island stack (character card / vitals / conditions, H2).
   Bounded above the dock + caption reserved space; scrolls internally. The
   top offset clears the top-anchored brand element (design D5/D10). */
.elosern-stage [data-anchor="hud-left"] {
  top: 64px;
  left: 16px;
   width: 262px;
   z-index: 4;
   display: flex;
   flex-direction: column;
   gap: 9px;
   max-height: calc(100% - var(--dock-h) - 110px);
   overflow-y: auto;
   overflow-x: hidden;
 }
 .elosern-stage [data-anchor="hud-right"] {
   top: 64px;
   right: 16px;
   width: 230px;
  z-index: 4;
  display: flex;
  flex-direction: column;
  gap: 9px;
   align-items: flex-end;
   max-height: calc(100% - var(--dock-h) - 110px);
  overflow-y: auto;
  overflow-x: hidden;
}

 /* feed: the bounded lower-centre narrative caption (design D4). The
    width is constrained to the clear space between the two HUD islands so
    the caption never intersects them at the supported viewports. */
.elosern-stage [data-anchor="feed"] {
  left: 50%;
  transform: translateX(-50%);
  bottom: calc(var(--dock-h) + 60px);
  width: min(880px, calc(90vw - 524px));
  z-index: 3;
}

/* dock: the floating action dock, sized from the shared --dock-h token. */
.elosern-stage [data-anchor="dock"] {
  left: 0;
  right: 0;
  bottom: 46px;
  height: var(--dock-h);
  z-index: 5;
}

/* command-line: the persistent command line (H5 upgrades the chrome). */
.elosern-stage [data-anchor="command-line"] {
  left: 0;
  right: 0;
  bottom: 0;
  height: 46px;
  z-index: 6;
}

/* Mode-gated visibility (design D2): CSS-only on data-elosern-mode,
   display:none so hidden surfaces leave the a11y tree and tab order. The
   matrix: the narrative caption, the HUD island stack (hud-left), and the
   command line are hidden in creation; the minimap is hidden in combat and
   creation; the dock and the scene backdrop stay visible in every mode. */
.elosern-stage[data-elosern-mode="creation"] [data-anchor="feed"],
.elosern-stage[data-elosern-mode="creation"] [data-anchor="hud-left"],
.elosern-stage[data-elosern-mode="creation"] [data-anchor="command-line"] {
  display: none;
}
.elosern-stage[data-elosern-mode="combat"] .local-map,
.elosern-stage[data-elosern-mode="creation"] .local-map {
  display: none !important;
}

/* The open-surface registry (design D9): when a drawer or overlay is open
   the stage is visually recessed; the mark clears only when nothing is
   open. The transition is token-gated, so prefers-reduced-motion disables
   it at the token level while the recessed state still applies. */
.elosern-stage[data-menu-open="true"] .stage-anchor {
  filter: var(--menu-open-filter);
  transition: filter var(--motion-base) var(--ease-standard);
}
</style>
